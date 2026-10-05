import logging
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ..schemas.claim import ClaimCreate

logger = logging.getLogger(__name__)


class ClaimService:
    """Service encapsulating coffee shop ownership claim lifecycle and authorization checks."""

    def submit_claim(
        self,
        shop_id: UUID,
        user_id: UUID,
        claim_in: ClaimCreate,
        supabase: Client,
    ) -> dict:
        """Submit a new ownership claim for an approved coffee shop.

        Enforces:
        - Target shop existence and APPROVED curation status (fail-closed)
        - Single active approved owner per shop (409 Conflict)
        - Single pending claim per user per shop (409 Conflict)
        - Rejection of claims from users who already own the shop (409 Conflict)
        """
        str_shop_id = str(shop_id)
        str_user_id = str(user_id)

        # 1. Verify shop existence
        try:
            shop_res = supabase.table("shops").select("id").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
        except APIError as exc:
            logger.error(f"Database error verifying coffee shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying the coffee shop.",
            )

        # 2. Verify shop curation status is APPROVED
        try:
            curation_res = supabase.table("shop_curation").select("status").eq("shop_id", str_shop_id).execute()
            curation_status = curation_res.data[0]["status"] if curation_res.data else "PENDING_REVIEW"
            if curation_status != "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Only approved coffee shops can be claimed.",
                )
        except APIError as exc:
            logger.error(f"Database error checking curation for shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while checking shop eligibility.",
            )

        # 3. Check if caller already has an active or pending claim for this shop
        try:
            user_claims_res = (
                supabase.table("shop_claims")
                .select("id, status")
                .eq("shop_id", str_shop_id)
                .eq("user_id", str_user_id)
                .execute()
            )
            for existing in user_claims_res.data or []:
                if existing.get("status") == "APPROVED":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You are already the verified owner of this coffee shop.",
                    )
                if existing.get("status") == "PENDING":
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="You already have a pending claim for this coffee shop.",
                    )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking user claims for shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while checking your claims.",
            )

        # 4. Check if shop is already claimed (has an APPROVED claim by another user)
        try:
            approved_res = (
                supabase.table("shop_claims")
                .select("id")
                .eq("shop_id", str_shop_id)
                .eq("status", "APPROVED")
                .execute()
            )
            if approved_res.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This coffee shop has already been claimed.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking approved claims for shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while checking existing claims.",
            )


        # 5. Insert new PENDING claim
        payload = {
            "shop_id": str_shop_id,
            "user_id": str_user_id,
            "status": "PENDING",
            "claimant_name": claim_in.claimant_name,
            "claimant_phone": claim_in.claimant_phone,
            "claimant_role": claim_in.claimant_role,
            "business_proof": claim_in.business_proof,
        }

        try:
            insert_res = supabase.table("shop_claims").insert(payload).execute()
            if not insert_res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to submit coffee shop ownership claim.",
                )
            return insert_res.data[0]
        except APIError as exc:
            logger.warning(f"Database error inserting claim for shop {str_shop_id}: {exc.message}")
            if exc.code == "23505":
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A conflicting claim already exists for this coffee shop.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while submitting your claim.",
            )

    def get_shop_claim_status(
        self,
        shop_id: UUID,
        user_id: UUID,
        supabase: Client,
    ) -> Optional[dict]:
        """Retrieve caller's latest claim for a specific coffee shop, or None."""
        try:
            res = (
                supabase.table("shop_claims")
                .select("*")
                .eq("shop_id", str(shop_id))
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .limit(1)
                .execute()
            )
            return res.data[0] if res.data else None
        except APIError as exc:
            logger.error(f"Database error retrieving claim status for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving claim status.",
            )

    def list_user_claims(
        self,
        user_id: UUID,
        supabase: Client,
    ) -> list[dict]:
        """Retrieve all claims submitted by the authenticated user."""
        try:
            res = (
                supabase.table("shop_claims")
                .select("*")
                .eq("user_id", str(user_id))
                .order("created_at", desc=True)
                .execute()
            )
            return res.data or []
        except APIError as exc:
            logger.error(f"Database error listing user claims: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while listing your claims.",
            )

    def list_claims(
        self,
        supabase: Client,
        status_filter: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Retrieve paginated list of claims with optional status filtering (Curator only)."""
        try:
            query = (
                supabase.table("shop_claims")
                .select("*, shop:shops(*)")
                .order("created_at", desc=True)
                .range(offset, offset + limit - 1)
            )
            if status_filter:
                query = query.eq("status", status_filter.upper())
            res = query.execute()
            return res.data or []
        except APIError as exc:
            logger.error(f"Database error listing claims for curator: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while listing claims.",
            )

    def get_claim_detail(
        self,
        claim_id: UUID,
        supabase: Client,
    ) -> dict:
        """Retrieve complete claim details by ID (Curator only)."""
        try:
            res = (
                supabase.table("shop_claims")
                .select("*, shop:shops(*)")
                .eq("id", str(claim_id))
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ownership claim not found.",
                )
            return res.data[0]
        except APIError as exc:
            logger.error(f"Database error retrieving claim {claim_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving claim details.",
            )

    def approve_claim(
        self,
        claim_id: UUID,
        curator_id: UUID,
        review_notes: Optional[str],
        supabase: Client,
    ) -> dict:
        """Approve a pending claim, establishing the claimant as verified owner (Curator only).

        Translates database partial unique index violations (code 23505) into HTTP 409 Conflict.
        """
        rpc_params = {
            "p_claim_id": str(claim_id),
            "p_curator_id": str(curator_id),
            "p_review_notes": review_notes,
        }
        try:
            res = supabase.rpc("approve_shop_claim", rpc_params).execute()
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to approve ownership claim.",
                )
            return self.get_claim_detail(claim_id, supabase)
        except HTTPException:
            raise
        except APIError as exc:
            logger.warning(f"Database error approving claim {claim_id}: {exc.message}")
            if exc.code == "23505" or "unique constraint" in (exc.message or "").lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="This coffee shop already has an approved owner.",
                )
            if exc.code == "P0001" or "not currently approved" in (exc.message or "").lower():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot approve claim: coffee shop is not currently approved for public discovery.",
                )
            if exc.code in ("P0003", "P0005") or "status changed" in (exc.message or "").lower() or "only pending" in (exc.message or "").lower():
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Claim status changed during review. Reload and try again.",
                )
            if exc.code == "P0002" or "not found" in (exc.message or "").lower():
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Ownership claim not found.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while approving the claim.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error approving claim {claim_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def reject_claim(
        self,
        claim_id: UUID,
        curator_id: UUID,
        review_notes: Optional[str],
        supabase: Client,
    ) -> dict:
        """Reject a pending claim (Curator only)."""
        claim = self.get_claim_detail(claim_id, supabase)
        if claim.get("status") != "PENDING":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject a claim with status '{claim.get('status')}'. Only PENDING claims can be rejected.",
            )

        now_utc = datetime.now(timezone.utc).isoformat()
        try:
            update_res = (
                supabase.table("shop_claims")
                .update({
                    "status": "REJECTED",
                    "curator_id": str(curator_id),
                    "review_notes": review_notes,
                    "reviewed_at": now_utc,
                })
                .eq("id", str(claim_id))
                .eq("status", "PENDING")
                .execute()
            )
            if not update_res.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Claim status changed during review. Reload and try again.",
                )
            return self.get_claim_detail(claim_id, supabase)
        except APIError as exc:
            logger.error(f"Database error rejecting claim {claim_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while rejecting the claim.",
            )

    def revoke_claim(
        self,
        claim_id: UUID,
        curator_id: UUID,
        review_notes: Optional[str],
        supabase: Client,
    ) -> dict:
        """Revoke a previously approved claim (Curator only)."""
        claim = self.get_claim_detail(claim_id, supabase)
        if claim.get("status") != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot revoke a claim with status '{claim.get('status')}'. Only APPROVED claims can be revoked.",
            )

        now_utc = datetime.now(timezone.utc).isoformat()
        try:
            update_res = (
                supabase.table("shop_claims")
                .update({
                    "status": "REVOKED",
                    "curator_id": str(curator_id),
                    "review_notes": review_notes,
                    "reviewed_at": now_utc,
                })
                .eq("id", str(claim_id))
                .eq("status", "APPROVED")
                .execute()
            )
            if not update_res.data:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Claim status changed during review. Reload and try again.",
                )
            return self.get_claim_detail(claim_id, supabase)
        except APIError as exc:
            logger.error(f"Database error revoking claim {claim_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while revoking the claim.",
            )
