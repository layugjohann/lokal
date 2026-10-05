import logging
from typing import Optional
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ..schemas.owner import OwnerShopUpdate
from ..schemas.review import UnifiedReview

logger = logging.getLogger(__name__)


class OwnerService:
    """Service encapsulating coffee shop owner dashboard data and safe listing updates."""

    def verify_active_owner(
        self,
        shop_id: UUID,
        user_id: UUID,
        supabase: Client,
    ) -> dict:
        """Verify that the user possesses an APPROVED claim for the shop and shop curation is APPROVED.

        Fails closed with HTTP 403 if:
        - The user does not have an approved claim
        - The shop's curation status is not APPROVED (e.g. EXCLUDED or PENDING_REVIEW)
        """
        str_shop_id = str(shop_id)
        str_user_id = str(user_id)

        # 1. Verify caller has an APPROVED claim for this shop
        try:
            claim_res = (
                supabase.table("shop_claims")
                .select("*")
                .eq("shop_id", str_shop_id)
                .eq("user_id", str_user_id)
                .eq("status", "APPROVED")
                .execute()
            )
            if not claim_res.data:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You do not have approved owner permissions for this coffee shop.",
                )
            active_claim = claim_res.data[0]
        except APIError as exc:
            logger.error(f"Database error verifying owner claim for shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying ownership authorization.",
            )

        # 2. Verify shop curation status is APPROVED
        try:
            curation_res = supabase.table("shop_curation").select("status").eq("shop_id", str_shop_id).execute()
            curation_status = curation_res.data[0]["status"] if curation_res.data else "PENDING_REVIEW"
            if curation_status != "APPROVED":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Coffee shop listing is not approved. Owner operations are unavailable.",
                )
        except APIError as exc:
            logger.error(f"Database error checking curation status for shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying shop eligibility.",
            )

        return active_claim

    def get_dashboard(
        self,
        shop_id: UUID,
        user_id: UUID,
        supabase: Client,
    ) -> dict:
        """Retrieve aggregated dashboard information for a claimed coffee shop."""
        active_claim = self.verify_active_owner(shop_id, user_id, supabase)
        str_shop_id = str(shop_id)

        # Fetch shop details
        try:
            shop_res = supabase.table("shops").select("*").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            shop = shop_res.data[0]
        except APIError as exc:
            logger.error(f"Database error retrieving shop {str_shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving coffee shop data.",
            )

        # Fetch first-party LOKAL reviews
        try:
            reviews_res = (
                supabase.table("reviews")
                .select("*")
                .eq("shop_id", str_shop_id)
                .eq("source", "lokal")
                .order("created_at", desc=True)
                .limit(20)
                .execute()
            )
            raw_reviews = reviews_res.data or []
        except APIError as exc:
            logger.error(f"Database error retrieving reviews for shop {str_shop_id}: {exc.message}")
            raw_reviews = []

        # Compute community metrics
        lokal_reviews_count = len(raw_reviews)
        lokal_rating: Optional[float] = None
        if lokal_reviews_count > 0:
            total_stars = sum(r.get("rating", 0) for r in raw_reviews if r.get("rating") is not None)
            valid_count = sum(1 for r in raw_reviews if r.get("rating") is not None)
            if valid_count > 0:
                lokal_rating = round(total_stars / valid_count, 2)

        # Build sanitized recent reviews (stripping user UUIDs and emails)
        recent_reviews = [
            UnifiedReview(
                id=str(r.get("id")),
                source="lokal",
                rating=float(r.get("rating", 5)),
                text=r.get("content"),
                author={"display_name": r.get("author_name") or "LOKAL User"},
                published_at=r.get("created_at"),
                updated_at=r.get("updated_at"),
            )
            for r in raw_reviews[:5]
        ]


        return {
            "shop": shop,
            "claim": active_claim,
            "lokal_rating": lokal_rating,
            "lokal_reviews_count": lokal_reviews_count,
            "rating": shop.get("rating"),
            "recent_reviews": recent_reviews,
        }

    def update_shop(
        self,
        shop_id: UUID,
        user_id: UUID,
        shop_in: OwnerShopUpdate,
        supabase: Client,
    ) -> dict:
        """Update only safe, owner-permitted fields (name, address) on the claimed coffee shop.

        Enforces that extra or protected fields (already rejected by OwnerShopUpdate extra='forbid')
        cannot be persisted.
        """
        self.verify_active_owner(shop_id, user_id, supabase)
        str_shop_id = str(shop_id)

        raw_updates = shop_in.model_dump(exclude_unset=True)
        # Defense in depth: strictly whitelist only name and address
        update_data = {k: v for k, v in raw_updates.items() if k in ("name", "address")}

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field must be provided for update.",
            )

        try:
            result = (
                supabase.table("shops")
                .update(update_data)
                .eq("id", str_shop_id)
                .execute()
            )
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            return result.data[0]
        except APIError as exc:
            logger.error(f"Database error updating shop {str_shop_id} by owner: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while updating the coffee shop.",
            )
