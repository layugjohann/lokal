from datetime import datetime, timezone
import logging
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ...schemas.curation import (
    CurationEvaluationResponse,
    ShopCurationResponse,
    ShopEligibilityStatus,
)
from .classifier import EligibilityClassifier
from .evidence_provider import GooglePlacesEvidenceProvider

logger = logging.getLogger(__name__)


class CurationService:
    """Orchestrates shop eligibility evaluation, manual curation overrides, and audit logging."""

    def __init__(self, classifier: Optional[EligibilityClassifier] = None) -> None:
        self.classifier = classifier or EligibilityClassifier(provider=GooglePlacesEvidenceProvider())

    def initialize_curation(self, shop_id: UUID, supabase: Client) -> dict:
        """Create an initial PENDING_REVIEW curation record for a newly ingested shop."""
        payload = {
            "shop_id": str(shop_id),
            "status": ShopEligibilityStatus.PENDING_REVIEW.value,
            "confidence": "LOW",
            "is_manual_override": False,
        }
        try:
            res = supabase.table("shop_curation").upsert(payload).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to initialize shop curation record.",
                )
            return res.data[0]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Failed to initialize curation for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while initializing shop curation.",
            ) from exc

    def get_curation(self, shop_id: UUID, supabase: Client) -> ShopCurationResponse:
        """Retrieve the current curation and eligibility state for a coffee shop."""
        try:
            res = supabase.table("shop_curation").select("*").eq("shop_id", str(shop_id)).execute()
            if not res.data:
                # If shop exists in shops table, auto-initialize
                shop_res = supabase.table("shops").select("id").eq("id", str(shop_id)).execute()
                if not shop_res.data:
                    raise HTTPException(
                        status_code=status.HTTP_404_NOT_FOUND,
                        detail="Coffee shop not found.",
                    )
                initialized = self.initialize_curation(shop_id, supabase)
                return ShopCurationResponse.model_validate(initialized)
            return ShopCurationResponse.model_validate(res.data[0])
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error fetching curation for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving curation record.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error retrieving curation for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    async def evaluate_shop(
        self, shop_id: UUID, supabase: Client, force: bool = False
    ) -> CurationEvaluationResponse:
        """Run automated eligibility classification for a shop and persist the decision."""
        # 1. Verify shop exists in shops table
        try:
            shop_res = supabase.table("shops").select("*").eq("id", str(shop_id)).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            shop = shop_res.data[0]
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Error fetching shop {shop_id} for evaluation: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while fetching coffee shop.",
            )

        # 2. Check current curation state
        curation_res = (
            supabase.table("shop_curation").select("*").eq("shop_id", str(shop_id)).execute()
        )
        current_curation = curation_res.data[0] if curation_res.data else None

        if current_curation and current_curation.get("is_manual_override") and not force:
            logger.info(
                f"Shop {shop_id} is locked under manual override. Skipping automated evaluation."
            )
            return CurationEvaluationResponse(
                shop_id=str(shop_id),
                status=ShopEligibilityStatus(current_curation["status"]),
                location_count=current_curation.get("location_count"),
                evidence_source=current_curation.get("evidence_source"),
                confidence=current_curation.get("confidence"),
                is_manual_override=True,
                evaluated_at=current_curation.get("evaluated_at"),
                message="Shop is locked under manual curation override. Use force=True to override.",
            )

        # 3. Execute classification
        decision = await self.classifier.classify(
            shop_name=shop["name"],
            shop_place_id=shop.get("google_place_id"),
        )

        now_iso = datetime.now(timezone.utc).isoformat()

        # Check concurrency: ensure manual override was not applied while classification ran
        if not force:
            latest_check = (
                supabase.table("shop_curation")
                .select("is_manual_override, status, location_count")
                .eq("shop_id", str(shop_id))
                .execute()
            )
            if latest_check.data and latest_check.data[0].get("is_manual_override"):
                logger.warning(
                    f"Shop {shop_id} was manually overridden while classification ran. Preserving manual state."
                )
                return CurationEvaluationResponse(
                    shop_id=str(shop_id),
                    status=ShopEligibilityStatus(latest_check.data[0]["status"]),
                    location_count=latest_check.data[0].get("location_count"),
                    evidence_source="manual",
                    confidence=CurationConfidence.HIGH,
                    is_manual_override=True,
                    evaluated_at=now_iso,
                    message="Manual override applied during evaluation was preserved.",
                )

        curation_payload = {
            "shop_id": str(shop_id),
            "status": decision.status.value,
            "location_count": decision.location_count,
            "evidence_source": decision.evidence_source,
            "confidence": decision.confidence.value,
            "is_manual_override": False,
            "curator_id": None,
            "curator_notes": decision.reason,
            "evaluated_at": now_iso,
        }

        # 4. Persist updated curation state
        try:
            supabase.table("shop_curation").upsert(curation_payload).execute()
        except Exception as exc:
            logger.error(f"Failed to update curation for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while saving evaluation results.",
            ) from exc

        # 5. Log audit record
        audit_payload = {
            "shop_id": str(shop_id),
            "old_status": current_curation.get("status") if current_curation else None,
            "new_status": decision.status.value,
            "old_location_count": current_curation.get("location_count") if current_curation else None,
            "new_location_count": decision.location_count,
            "changed_by": None,
            "change_source": "automated_evaluation",
            "reason": decision.reason,
        }
        try:
            supabase.table("shop_curation_audit").insert(audit_payload).execute()
        except Exception as exc:
            logger.error(f"Failed to log curation audit for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while recording curation audit trail.",
            ) from exc

        return CurationEvaluationResponse(
            shop_id=str(shop_id),
            status=decision.status,
            location_count=decision.location_count,
            evidence_source=decision.evidence_source,
            confidence=decision.confidence,
            is_manual_override=False,
            evaluated_at=now_iso,
            message=decision.reason,
        )

    def override_curation(
        self,
        shop_id: UUID,
        curator_id: UUID,
        status_in: ShopEligibilityStatus,
        reason: str,
        supabase: Client,
    ) -> ShopCurationResponse:
        """Apply an authorized manual curation override and record audit trail."""
        # 1. Verify shop exists
        shop_res = supabase.table("shops").select("id").eq("id", str(shop_id)).execute()
        if not shop_res.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found.",
            )

        # 2. Get current curation
        curation_res = (
            supabase.table("shop_curation").select("*").eq("shop_id", str(shop_id)).execute()
        )
        current = curation_res.data[0] if curation_res.data else None

        now_iso = datetime.now(timezone.utc).isoformat()
        update_payload = {
            "shop_id": str(shop_id),
            "status": status_in.value,
            "confidence": "HIGH",
            "is_manual_override": True,
            "curator_id": str(curator_id),
            "curator_notes": reason,
            "evaluated_at": now_iso,
        }

        # 3. Update curation
        try:
            res = supabase.table("shop_curation").upsert(update_payload).execute()
            updated_record = res.data[0]
        except Exception as exc:
            logger.error(f"Failed to apply curation override for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while saving manual override.",
            )

        # 4. Insert audit record
        audit_payload = {
            "shop_id": str(shop_id),
            "old_status": current.get("status") if current else None,
            "new_status": status_in.value,
            "old_location_count": current.get("location_count") if current else None,
            "new_location_count": current.get("location_count") if current else None,
            "changed_by": str(curator_id),
            "change_source": "manual_override",
            "reason": reason,
        }
        try:
            supabase.table("shop_curation_audit").insert(audit_payload).execute()
        except Exception as exc:
            logger.error(f"Failed to write curation audit log for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while recording curation audit trail.",
            ) from exc

        return ShopCurationResponse.model_validate(updated_record)
