import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas import (
    MessageResponse,
    ReviewCreate,
    ReviewUpdate,
    ShopReviewsResponse,
    UnifiedReview,
    UserResponse,
)
from ....services.reviews import ReviewService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_review_service() -> ReviewService:
    """Dependency provider for ReviewService."""
    return ReviewService()


@router.post(
    "/{shop_id}/reviews",
    response_model=UnifiedReview,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a review for a coffee shop",
)
def create_shop_review(
    shop_id: UUID,
    review_in: ReviewCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> UnifiedReview:
    """Submit a first-party LOKAL review for an approved coffee shop.

    Enforces 1 review per user per shop constraint and fail-closed curation approval.
    """
    return service.create_user_review(
        shop_id=shop_id,
        user=current_user,
        review_in=review_in,
        supabase=supabase,
    )


@router.get(
    "/{shop_id}/reviews/mine",
    response_model=UnifiedReview,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user's review for a coffee shop",
)
def get_my_review(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> UnifiedReview:
    """Retrieve the authenticated caller's own review for a coffee shop.

    Permitted even if the shop is currently excluded or pending review.
    """
    return service.get_user_review(
        shop_id=shop_id,
        user=current_user,
        supabase=supabase,
    )


@router.patch(
    "/{shop_id}/reviews/mine",
    response_model=UnifiedReview,
    status_code=status.HTTP_200_OK,
    summary="Update current user's review for a coffee shop",
)
def update_my_review(
    shop_id: UUID,
    review_in: ReviewUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> UnifiedReview:
    """Partially update the authenticated caller's review with field-presence semantics.

    Blocked if the coffee shop is not currently approved.
    """
    return service.update_user_review(
        shop_id=shop_id,
        user=current_user,
        review_in=review_in,
        supabase=supabase,
    )


@router.delete(
    "/{shop_id}/reviews/mine",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete current user's review for a coffee shop",
)
def delete_my_review(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[ReviewService, Depends(get_review_service)],
) -> MessageResponse:
    """Permanently delete the authenticated caller's review for a coffee shop.

    Permitted even if the coffee shop is currently excluded.
    """
    service.delete_user_review(
        shop_id=shop_id,
        user=current_user,
        supabase=supabase,
    )
    return MessageResponse(message="Review deleted successfully.")


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
    """Retrieve normalized unified reviews (first-party LOKAL + external) for an approved coffee shop.

    Returns 404 Not Found if the coffee shop is pending review or excluded.
    """
    return await service.get_shop_reviews(shop_id=shop_id, supabase=supabase)
