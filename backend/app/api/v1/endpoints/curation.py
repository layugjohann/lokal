import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user, require_curator
from ....schemas import (
    CurationEvaluationResponse,
    CurationOverrideRequest,
    ShopCurationResponse,
    UserResponse,
)
from ....services.curation import CurationService

logger = logging.getLogger(__name__)

router = APIRouter()
curation_service = CurationService()


@router.get(
    "/{shop_id}/curation",
    response_model=ShopCurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Get coffee shop curation status",
)
def get_shop_curation(
    shop_id: UUID,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> ShopCurationResponse:
    """Retrieve the current curation and eligibility record for a coffee shop."""
    return curation_service.get_curation(shop_id=shop_id, supabase=supabase)


@router.post(
    "/{shop_id}/curation/evaluate",
    response_model=CurationEvaluationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger automated eligibility evaluation for a shop",
)
async def evaluate_shop_curation(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    force: bool = Query(default=False, description="Re-evaluate even if manual override is active"),
) -> CurationEvaluationResponse:
    """Run automated location-count evidence collection and update eligibility status."""
    if force:
        require_curator(current_user)
    return await curation_service.evaluate_shop(shop_id=shop_id, supabase=supabase, force=force)


@router.post(
    "/{shop_id}/curation/override",
    response_model=ShopCurationResponse,
    status_code=status.HTTP_200_OK,
    summary="Apply manual curation override (Curator only)",
)
def override_shop_curation(
    shop_id: UUID,
    override_in: CurationOverrideRequest,
    curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> ShopCurationResponse:
    """Apply an authorized manual override to approve or exclude a shop, logging an audit trail."""
    curator_uuid = UUID(curator.id)
    return curation_service.override_curation(
        shop_id=shop_id,
        curator_id=curator_uuid,
        status_in=override_in.status,
        reason=override_in.reason,
        supabase=supabase,
    )
