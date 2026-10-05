import logging
from typing import Annotated, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, Query, status
from supabase import Client

from ...deps import (
    get_current_user,
    get_service_role_supabase,
    require_curator,
)
from ....schemas import (
    ClaimCreate,
    ClaimReviewRequest,
    ShopClaimDetailResponse,
    ShopClaimResponse,
    ShopClaimStatus,
    UserResponse,
)
from ....services.claims import ClaimService

logger = logging.getLogger(__name__)

shop_claims_router = APIRouter()
claims_router = APIRouter()
claim_service = ClaimService()


# ============================================================================
# User-Facing Claim Endpoints (prefix: /shops)
# ============================================================================

@shop_claims_router.post(
    "/{shop_id}/claim",
    response_model=ShopClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit coffee shop ownership claim",
)
def create_shop_claim(
    shop_id: UUID,
    claim_in: ClaimCreate,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopClaimResponse:
    """Submit a new ownership claim for an approved coffee shop.

    Requires authentication. Returns 400 if shop is not approved, or 409 if already claimed
    or duplicate pending claim.
    """
    user_uuid = UUID(current_user.id)
    return claim_service.submit_claim(
        shop_id=shop_id,
        user_id=user_uuid,
        claim_in=claim_in,
        supabase=supabase,
    )


@shop_claims_router.get(
    "/{shop_id}/claim",
    response_model=Optional[ShopClaimResponse],
    status_code=status.HTTP_200_OK,
    summary="Retrieve current user's claim status for a shop",
)
def get_shop_claim_status(
    shop_id: UUID,
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> Optional[ShopClaimResponse]:
    """Retrieve the current user's latest claim for a coffee shop, or null if unclaimed."""
    user_uuid = UUID(current_user.id)
    return claim_service.get_shop_claim_status(
        shop_id=shop_id,
        user_id=user_uuid,
        supabase=supabase,
    )


# ============================================================================
# User Claims & Curator Claims Endpoints (prefix: /claims)
# ============================================================================

@claims_router.get(
    "/mine",
    response_model=list[ShopClaimResponse],
    status_code=status.HTTP_200_OK,
    summary="List current user's submitted claims",
)
def list_my_claims(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> list[ShopClaimResponse]:
    """Retrieve all coffee shop claims submitted by the authenticated caller."""
    user_uuid = UUID(current_user.id)
    return claim_service.list_user_claims(
        user_id=user_uuid,
        supabase=supabase,
    )


@claims_router.get(
    "",
    response_model=list[ShopClaimDetailResponse],
    status_code=status.HTTP_200_OK,
    summary="List all coffee shop claims (Curator only)",
)
def list_claims(
    _curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
    status: Optional[ShopClaimStatus] = Query(default=None, description="Filter claims by status"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of claims to return"),
    offset: int = Query(default=0, ge=0, description="Number of claims to skip"),
) -> list[ShopClaimDetailResponse]:
    """Retrieve paginated list of claims with optional status filtering (Curator only)."""
    status_filter = status.value if status else None
    return claim_service.list_claims(
        supabase=supabase,
        status_filter=status_filter,
        limit=limit,
        offset=offset,
    )


@claims_router.get(
    "/{claim_id}",
    response_model=ShopClaimDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve claim details by ID (Curator only)",
)
def get_claim(
    claim_id: UUID,
    _curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopClaimDetailResponse:
    """Retrieve complete claim details and evidence notes for curator inspection (Curator only)."""
    return claim_service.get_claim_detail(
        claim_id=claim_id,
        supabase=supabase,
    )


@claims_router.post(
    "/{claim_id}/approve",
    response_model=ShopClaimDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Approve coffee shop ownership claim (Curator only)",
)
def approve_claim(
    claim_id: UUID,
    review_in: ClaimReviewRequest,
    curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopClaimDetailResponse:
    """Approve a pending claim, establishing claimant as verified owner (Curator only).

    Returns 409 Conflict if shop already has an approved owner.
    """
    curator_uuid = UUID(curator.id)
    return claim_service.approve_claim(
        claim_id=claim_id,
        curator_id=curator_uuid,
        review_notes=review_in.review_notes,
        supabase=supabase,
    )


@claims_router.post(
    "/{claim_id}/reject",
    response_model=ShopClaimDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Reject coffee shop ownership claim (Curator only)",
)
def reject_claim(
    claim_id: UUID,
    review_in: ClaimReviewRequest,
    curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopClaimDetailResponse:
    """Reject a pending ownership claim with recorded review notes (Curator only)."""
    curator_uuid = UUID(curator.id)
    return claim_service.reject_claim(
        claim_id=claim_id,
        curator_id=curator_uuid,
        review_notes=review_in.review_notes,
        supabase=supabase,
    )


@claims_router.post(
    "/{claim_id}/revoke",
    response_model=ShopClaimDetailResponse,
    status_code=status.HTTP_200_OK,
    summary="Revoke previously approved ownership claim (Curator only)",
)
def revoke_claim(
    claim_id: UUID,
    review_in: ClaimReviewRequest,
    curator: Annotated[UserResponse, Depends(require_curator)],
    supabase: Annotated[Client, Depends(get_service_role_supabase)],
) -> ShopClaimDetailResponse:
    """Revoke a previously approved ownership claim (Curator only)."""
    curator_uuid = UUID(curator.id)
    return claim_service.revoke_claim(
        claim_id=claim_id,
        curator_id=curator_uuid,
        review_notes=review_in.review_notes,
        supabase=supabase,
    )
