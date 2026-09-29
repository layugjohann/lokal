import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas import (
    FavoriteStatusResponse,
    MessageResponse,
    UserResponse,
)
from ....services.favorites import FavoriteService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_favorite_service() -> FavoriteService:
    """Dependency provider for FavoriteService."""
    return FavoriteService()


@router.get(
    "/{shop_id}/favorite",
    response_model=FavoriteStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user's favorite status for a coffee shop",
)
def get_shop_favorite_status(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[FavoriteService, Depends(get_favorite_service)],
) -> FavoriteStatusResponse:
    """Retrieve whether the authenticated user has favorited an approved coffee shop.

    Requires authentication and APPROVED shop curation status.
    Returns 404 Not Found if the shop does not exist or is not approved.
    """
    return service.get_favorite_status(
        shop_id=shop_id,
        user=current_user,
        supabase=supabase,
    )


@router.post(
    "/{shop_id}/favorite",
    response_model=FavoriteStatusResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Favorite a coffee shop",
)
def create_shop_favorite(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[FavoriteService, Depends(get_favorite_service)],
) -> FavoriteStatusResponse:
    """Add an approved coffee shop to the authenticated user's favorites.

    Enforces APPROVED shop curation status and uniqueness.
    Returns 409 Conflict if already favorited.
    """
    return service.add_favorite(
        shop_id=shop_id,
        user=current_user,
        supabase=supabase,
    )


@router.delete(
    "/{shop_id}/favorite",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Unfavorite a coffee shop",
)
def delete_shop_favorite(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[FavoriteService, Depends(get_favorite_service)],
) -> MessageResponse:
    """Remove a coffee shop from the authenticated user's favorites.

    Returns 404 Not Found if the coffee shop was not in the caller's favorites.
    Permitted even if the shop is excluded or pending review.
    """
    service.remove_favorite(
        shop_id=shop_id,
        user=current_user,
        supabase=supabase,
    )
    return MessageResponse(message="Coffee shop removed from favorites.")
