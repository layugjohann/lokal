from datetime import datetime
import logging
from typing import Any, Optional, Union
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ...schemas.auth import UserResponse
from ...schemas.review import (
    ReviewAuthor,
    ReviewCreate,
    ReviewSource,
    ReviewUpdate,
    ShopReviewsResponse,
    UnifiedReview,
)
from .base import BaseReviewProvider, ExternalProviderError
from .google_places import GooglePlacesReviewProvider

logger = logging.getLogger(__name__)


def _parse_timestamp(val: Any) -> Optional[datetime]:
    """Parse a datetime object or ISO string timestamp safely."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def _row_to_unified_review(row: dict[str, Any]) -> UnifiedReview:
    """Normalize a database review row into a provider-neutral UnifiedReview."""
    c_dt = _parse_timestamp(row.get("created_at"))
    u_dt = _parse_timestamp(row.get("updated_at"))
    is_edited = bool(c_dt and u_dt and u_dt > c_dt)

    return UnifiedReview(
        id=f"lokal:{row['id']}",
        source=ReviewSource.LOKAL,
        rating=float(row["rating"]),
        text=row.get("content"),
        original_text=row.get("content"),
        language=None,
        author=ReviewAuthor(
            display_name=row.get("author_name") or "LOKAL User",
            avatar_url=None,
            profile_url=None,
        ),
        published_at=c_dt,
        updated_at=u_dt if is_edited else None,
        is_edited=is_edited,
        relative_time=None,
        report_url=None,
    )


class ReviewService:
    """Service layer orchestrating coffee shop review retrieval and normalization."""

    def __init__(self, provider: Optional[BaseReviewProvider] = None) -> None:
        self.provider = provider or GooglePlacesReviewProvider()

    def _get_shop_curation_status(self, shop_id: str, supabase: Client) -> str:
        """Retrieve the curation status of a shop. Defaults to PENDING_REVIEW (fail-closed)."""
        try:
            curation_res = (
                supabase.table("shop_curation")
                .select("status")
                .eq("shop_id", shop_id)
                .execute()
            )
            if curation_res.data:
                return curation_res.data[0].get("status", "PENDING_REVIEW")
            return "PENDING_REVIEW"
        except Exception as exc:
            logger.warning(f"Failed to fetch curation status for shop {shop_id}: {exc}")
            return "PENDING_REVIEW"

    async def get_shop_reviews(
        self, shop_id: Union[UUID, str], supabase: Client
    ) -> ShopReviewsResponse:
        """Retrieve unified reviews and separate metrics for a LOKAL-supported coffee shop.

        Args:
            shop_id: Unique UUID of the coffee shop in LOKAL.
            supabase: Authenticated request-scoped Supabase client.

        Returns:
            ShopReviewsResponse containing unified reviews and separate Google & LOKAL metrics.

        Raises:
            HTTPException: 404 if the coffee shop does not exist or is not APPROVED.
            HTTPException: 502 if the external review provider fails or times out.
            HTTPException: 500 on database communication errors.
        """
        str_shop_id = str(shop_id)

        try:
            result = supabase.table("shops").select("*").eq("id", str_shop_id).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            shop = result.data[0]
        except APIError as exc:
            logger.error(f"Database error retrieving coffee shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving the coffee shop.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error retrieving coffee shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

        # Curation enforcement (fail-closed: unapproved or excluded shops return 404 to standard users)
        curation_status = self._get_shop_curation_status(str_shop_id, supabase)
        if curation_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found.",
            )

        # 1. Fetch first-party LOKAL user reviews
        lokal_reviews: list[UnifiedReview] = []
        try:
            reviews_res = (
                supabase.table("reviews")
                .select("*")
                .eq("shop_id", str_shop_id)
                .eq("source", "lokal")
                .order("created_at", desc=True)
                .execute()
            )
            if reviews_res.data:
                lokal_reviews = [_row_to_unified_review(row) for row in reviews_res.data]
        except APIError as exc:
            logger.error(f"Database error fetching user reviews for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving user reviews.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error fetching user reviews for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

        lokal_count = len(lokal_reviews)
        lokal_avg = (
            round(sum(r.rating for r in lokal_reviews) / lokal_count, 2)
            if lokal_count > 0
            else None
        )

        # 2. Fetch external reviews from Google Places provider if place ID is available
        google_place_id = shop.get("google_place_id")
        external_reviews: list[UnifiedReview] = []
        attributions = []
        resolved_rating = shop.get("rating")
        resolved_count = 0

        if google_place_id:
            try:
                ext_revs, attribution, avg_rating, total_count = await self.provider.fetch_reviews(
                    google_place_id
                )
                external_reviews = ext_revs
                if attribution and (external_reviews or attribution.source_url):
                    attributions = [attribution]
                resolved_rating = avg_rating if avg_rating is not None else shop.get("rating")
                resolved_count = total_count if total_count is not None else len(external_reviews)
            except ExternalProviderError as exc:
                logger.warning(
                    f"External review provider failure for shop {shop_id} ({google_place_id}): {exc}"
                )
                raise HTTPException(
                    status_code=status.HTTP_502_BAD_GATEWAY,
                    detail="External review provider temporarily unavailable.",
                )

        # 3. Combine reviews into unified domain (LOKAL reviews first, then external reviews)
        merged_reviews = lokal_reviews + external_reviews

        return ShopReviewsResponse(
            shop_id=shop_id,
            average_rating=resolved_rating,
            total_reviews_count=resolved_count,
            lokal_average_rating=lokal_avg,
            lokal_reviews_count=lokal_count,
            reviews=merged_reviews,
            attributions=attributions,
            has_more=False,
        )

    def create_user_review(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        review_in: ReviewCreate,
        supabase: Client,
    ) -> UnifiedReview:
        """Create a new LOKAL first-party user review.

        Args:
            shop_id: Unique UUID of the coffee shop.
            user: Authenticated caller user.
            review_in: Validated review creation payload.
            supabase: Request-scoped authenticated Supabase client.

        Returns:
            Created UnifiedReview object.
        """
        str_shop_id = str(shop_id)

        # Verify shop existence
        try:
            shop_res = supabase.table("shops").select("id").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying the coffee shop.",
            )

        # Verify shop curation status
        curation_status = self._get_shop_curation_status(str_shop_id, supabase)
        if curation_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot review a coffee shop that is not approved for public discovery.",
            )

        # Resolve author display name snapshot safely from user metadata
        metadata = user.user_metadata or {}
        raw_name = ""
        for field in ("full_name", "display_name"):
            candidate = metadata.get(field)
            if isinstance(candidate, str) and candidate.strip():
                raw_name = candidate.strip()
                break
        author_name = raw_name if raw_name else "LOKAL User"

        # Invoke secure database RPC with strictly unforgeable server-side fields
        rpc_params = {
            "p_shop_id": str_shop_id,
            "p_rating": review_in.rating,
            "p_content": review_in.content,
        }

        try:
            result = supabase.rpc("create_user_review", rpc_params).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to persist review record.",
                )
            row = result.data if isinstance(result.data, dict) else result.data[0]
            return _row_to_unified_review(row)
        except APIError as exc:
            logger.warning(f"Database error inserting review for shop {shop_id}: {exc.message}")
            if exc.code == "23505" or "already reviewed" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You have already reviewed this coffee shop. You can edit your existing review.",
                )
            if exc.code == "P0001" or "not approved" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot review a coffee shop that is not approved for public discovery.",
                )
            if exc.code == "P0002" or "not found" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while saving your review.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error saving review for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def get_user_review(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        supabase: Client,
    ) -> UnifiedReview:
        """Retrieve the authenticated user's own review for a shop.

        Allowed even if shop is EXCLUDED or PENDING_REVIEW per PO decision.
        """
        str_shop_id = str(shop_id)

        try:
            res = (
                supabase.table("reviews")
                .select("*")
                .eq("shop_id", str_shop_id)
                .eq("user_id", user.id)
                .eq("source", "lokal")
                .execute()
            )
            if not res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="You have not reviewed this coffee shop.",
                )
            return _row_to_unified_review(res.data[0])
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error retrieving user review for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving your review.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error retrieving user review for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def update_user_review(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        review_in: ReviewUpdate,
        supabase: Client,
    ) -> UnifiedReview:
        """Partially update an existing review with strict field-presence semantics.

        Args:
            shop_id: Unique UUID of the coffee shop.
            user: Authenticated caller user.
            review_in: Validated partial update payload.
            supabase: Request-scoped authenticated Supabase client.

        Returns:
            Updated UnifiedReview object.
        """
        str_shop_id = str(shop_id)

        # Field-presence check: empty body is rejected
        update_fields = review_in.model_dump(exclude_unset=True)
        if not update_fields:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one field ('rating' or 'content') must be provided for update.",
            )

        # Verify shop existence
        try:
            shop_res = supabase.table("shops").select("id").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying the coffee shop.",
            )

        # Verify curation status: editing is blocked while shop is not APPROVED
        curation_status = self._get_shop_curation_status(str_shop_id, supabase)
        if curation_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot edit reviews for a coffee shop that is not approved for public discovery.",
            )

        # Check existing review ownership
        try:
            existing = (
                supabase.table("reviews")
                .select("id")
                .eq("shop_id", str_shop_id)
                .eq("user_id", user.id)
                .eq("source", "lokal")
                .execute()
            )
            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="You have not reviewed this coffee shop.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error verifying review existence: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying your review.",
            )

        # Invoke secure database RPC for partial update
        has_content_update = "content" in update_fields
        rpc_params = {
            "p_shop_id": str_shop_id,
            "p_rating": update_fields.get("rating"),
            "p_content": update_fields.get("content"),
            "p_update_content": has_content_update,
        }

        try:
            result = supabase.rpc("update_user_review", rpc_params).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update review record.",
                )
            row = result.data if isinstance(result.data, dict) else result.data[0]
            return _row_to_unified_review(row)
        except APIError as exc:
            logger.warning(f"Database error updating review for shop {shop_id}: {exc.message}")
            if exc.code == "P0001" or "not approved" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot edit reviews for a coffee shop that is not approved for public discovery.",
                )
            if exc.code == "P0002" or "not reviewed" in (exc.message or "") or "not found" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="You have not reviewed this coffee shop.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while updating your review.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error updating review for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def delete_user_review(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        supabase: Client,
    ) -> None:
        """Permanently delete the user's review.

        Allowed even if shop is EXCLUDED or PENDING_REVIEW per PO decision.
        """
        str_shop_id = str(shop_id)

        try:
            existing = (
                supabase.table("reviews")
                .select("id")
                .eq("shop_id", str_shop_id)
                .eq("user_id", user.id)
                .eq("source", "lokal")
                .execute()
            )
            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="You have not reviewed this coffee shop.",
                )

            supabase.table("reviews").delete().eq("shop_id", str_shop_id).eq("user_id", user.id).eq("source", "lokal").execute()
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error deleting review for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while deleting your review.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error deleting review for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )
