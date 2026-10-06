import logging
from typing import Annotated
from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas import CommunityFeedResponse, UserResponse
from ....services.community import CommunityService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_community_service() -> CommunityService:
    """Dependency provider for CommunityService."""
    return CommunityService()


@router.get(
    "/feed",
    response_model=CommunityFeedResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve community feed of recent reviews",
)
def get_community_feed(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[CommunityService, Depends(get_community_service)],
    limit: int = Query(
        default=20,
        ge=1,
        le=50,
        description="Maximum number of feed items to return (1 to 50)",
    ),
    offset: int = Query(
        default=0,
        ge=0,
        description="Number of feed items to skip",
    ),
) -> CommunityFeedResponse:
    """Retrieve an authenticated chronological community feed of recent first-party LOKAL reviews.

    Only reviews for approved coffee shops are included.
    Deterministic newest-first ordering with secondary tie-breaker.
    Returns safe application identifiers (review id, shop_id) for client navigation and keying,
    while strictly excluding internal user UUIDs, email addresses, and curator metadata.
    """
    return service.get_community_feed(
        supabase=supabase,
        limit=limit,
        offset=offset,
    )
