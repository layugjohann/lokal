import logging
from typing import Optional, Union
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ...schemas.review import ShopReviewsResponse
from .base import BaseReviewProvider, ExternalProviderError
from .google_places import GooglePlacesReviewProvider

logger = logging.getLogger(__name__)


class ReviewService:
    """Service layer orchestrating coffee shop review retrieval and normalization."""

    def __init__(self, provider: Optional[BaseReviewProvider] = None) -> None:
        self.provider = provider or GooglePlacesReviewProvider()

    async def get_shop_reviews(
        self, shop_id: Union[UUID, str], supabase: Client
    ) -> ShopReviewsResponse:
        """Retrieve normalized reviews for a LOKAL-supported coffee shop.

        Args:
            shop_id: Unique UUID of the coffee shop in LOKAL.
            supabase: Authenticated request-scoped Supabase client.

        Returns:
            ShopReviewsResponse containing normalized reviews and provider attributions.

        Raises:
            HTTPException: 404 if the coffee shop does not exist.
            HTTPException: 502 if the external review provider fails or times out.
            HTTPException: 500 on database communication errors.
        """
        try:
            result = supabase.table("shops").select("*").eq("id", str(shop_id)).execute()
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

        google_place_id = shop.get("google_place_id")
        if not google_place_id:
            return ShopReviewsResponse(
                shop_id=shop_id,
                average_rating=shop.get("rating"),
                total_reviews_count=0,
                reviews=[],
                attributions=[],
                has_more=False,
            )

        try:
            reviews, attribution, avg_rating, total_count = await self.provider.fetch_reviews(
                google_place_id
            )
        except ExternalProviderError as exc:
            logger.warning(
                f"External review provider failure for shop {shop_id} ({google_place_id}): {exc}"
            )
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="External review provider temporarily unavailable.",
            )

        # Provider attribution is attached when reviews or external source links exist
        attributions = [attribution] if attribution and (reviews or attribution.source_url) else []

        # Architectural extension point: first-party LOKAL reviews will be merged here in a future feature

        resolved_rating = avg_rating if avg_rating is not None else shop.get("rating")
        resolved_count = total_count if total_count is not None else len(reviews)

        return ShopReviewsResponse(
            shop_id=shop_id,
            average_rating=resolved_rating,
            total_reviews_count=resolved_count,
            reviews=reviews,
            attributions=attributions,
            has_more=False,
        )
