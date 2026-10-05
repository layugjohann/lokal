import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, status
from supabase import Client

from ...deps import get_current_user, get_service_role_supabase
from ....schemas import (
    OwnerDashboardResponse,
    OwnerShopUpdate,
    ShopResponse,
    UserResponse,
)
from ....services.owner import OwnerService

logger = logging.getLogger(__name__)

router = APIRouter()
owner_service = OwnerService()


@router.get(
    "/{shop_id}/dashboard",
    response_model=OwnerDashboardResponse,
    status_code=status.HTTP_200_OK,
    summary="Get coffee shop owner dashboard data",
)
def get_owner_dashboard(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> OwnerDashboardResponse:
    """Retrieve owner dashboard information for an approved claimed coffee shop.

    Requires that the caller holds an APPROVED claim for the shop and that shop curation
    status is currently APPROVED (returns 403 Forbidden otherwise).
    """
    user_uuid = UUID(current_user.id)
    return owner_service.get_dashboard(
        shop_id=shop_id,
        user_id=user_uuid,
        supabase=supabase,
    )


@router.patch(
    "/{shop_id}",
    response_model=ShopResponse,
    status_code=status.HTTP_200_OK,
    summary="Update coffee shop details by verified owner",
)
def update_shop_by_owner(
    shop_id: UUID,
    shop_in: OwnerShopUpdate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopResponse:
    """Update owner-permitted fields (name, address) for an approved claimed coffee shop.

    Protected fields (rating, coordinates, google_place_id, curation status) are strictly
    forbidden at the request boundary (returns 422 Unprocessable Entity).
    Requires active APPROVED claim and APPROVED shop curation (returns 403 Forbidden otherwise).
    """
    user_uuid = UUID(current_user.id)
    return owner_service.update_shop(
        shop_id=shop_id,
        user_id=user_uuid,
        shop_in=shop_in,
        supabase=supabase,
    )
