import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas import ShopReviewsResponse, UserResponse
from ....services.reviews import ReviewService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_review_service() -> ReviewService:
    """Dependency provider for ReviewService."""
    return ReviewService()


@router.get(
    "/{shop_id}/reviews",
    response_model=ShopReviewsResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve coffee shop reviews",
)
async def get_shop_reviews(
    shop_id: UUID,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> ShopReviewsResponse:
    """Retrieve normalized external reviews and attribution for a LOKAL-supported coffee shop.

    Reviews are loaded dynamically on demand and are not permanently persisted in the local database.
    """
    return await service.get_shop_reviews(shop_id=shop_id, supabase=supabase)
