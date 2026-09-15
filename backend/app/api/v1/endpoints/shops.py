import logging
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from postgrest.exceptions import APIError
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas import (
    MessageResponse,
    NearbyShopResponse,
    ShopCreate,
    ShopResponse,
    ShopUpdate,
    UserResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter()



@router.post(
    "",
    response_model=ShopResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new coffee shop",
)
def create_shop(
    shop_in: ShopCreate,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> ShopResponse:
    """Create a new coffee shop record in the database."""
    payload = shop_in.model_dump(exclude_unset=True)

    try:
        result = supabase.table("shops").insert(payload).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create coffee shop record.",
            )
        return result.data[0]
    except APIError as exc:
        logger.warning(f"Database error creating coffee shop: {exc.message}")
        if exc.code == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A coffee shop with this Google Place ID already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while creating the coffee shop.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error creating coffee shop: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )


@router.get(
    "",
    response_model=list[ShopResponse],
    status_code=status.HTTP_200_OK,
    summary="List coffee shops",
)
def list_shops(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of shops to return"),
    offset: int = Query(default=0, ge=0, description="Number of shops to skip"),
) -> list[ShopResponse]:
    """Retrieve a paginated list of coffee shops, ordered by name."""
    try:
        result = (
            supabase.table("shops")
            .select("*")
            .order("name")
            .range(offset, offset + limit - 1)
            .execute()
        )
        return result.data or []
    except APIError as exc:
        logger.error(f"Database error listing coffee shops: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while listing coffee shops.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error listing coffee shops: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )


@router.get(
    "/nearby",
    response_model=list[NearbyShopResponse],
    status_code=status.HTTP_200_OK,
    summary="Search nearby coffee shops",
)
def search_nearby_shops(
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    latitude: float = Query(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90.0 and 90.0"),
    longitude: float = Query(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180.0 and 180.0"),
    radius: float = Query(default=5000.0, gt=0.0, le=50000.0, description="Search radius in meters (max 50,000m)"),
    limit: int = Query(default=50, ge=1, le=100, description="Maximum number of shops to return"),
    offset: int = Query(default=0, ge=0, description="Number of shops to skip"),
) -> list[NearbyShopResponse]:
    """Retrieve nearby coffee shops within a given radius using bounding box and Haversine distance."""
    try:
        result = supabase.rpc(
            "get_nearby_shops",
            {
                "user_lat": latitude,
                "user_lng": longitude,
                "radius_meters": radius,
                "result_limit": limit,
                "result_offset": offset,
            },
        ).execute()
        return result.data or []
    except APIError as exc:
        logger.error(f"Database error searching nearby coffee shops: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while searching for nearby coffee shops.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error searching nearby coffee shops: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )


@router.get(
    "/{shop_id}",
    response_model=ShopResponse,
    status_code=status.HTTP_200_OK,
    summary="Retrieve coffee shop by ID",
)
def get_shop(
    shop_id: UUID,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> ShopResponse:
    """Retrieve details for a specific coffee shop by its UUID."""
    try:
        result = supabase.table("shops").select("*").eq("id", str(shop_id)).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found.",
            )
        return result.data[0]
    except APIError as exc:
        logger.error(f"Database error retrieving coffee shop {shop_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while retrieving the coffee shop.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error retrieving coffee shop: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )


@router.patch(
    "/{shop_id}",
    response_model=ShopResponse,
    status_code=status.HTTP_200_OK,
    summary="Update coffee shop",
)
def update_shop(
    shop_id: UUID,
    shop_in: ShopUpdate,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> ShopResponse:
    """Update fields of an existing coffee shop record."""
    update_data = shop_in.model_dump(exclude_unset=True)
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one field must be provided for update.",
        )

    try:
        result = (
            supabase.table("shops")
            .update(update_data)
            .eq("id", str(shop_id))
            .execute()
        )
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found.",
            )
        return result.data[0]
    except APIError as exc:
        logger.warning(f"Database error updating coffee shop {shop_id}: {exc.message}")
        if exc.code == "23505":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A coffee shop with this Google Place ID already exists.",
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while updating the coffee shop.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error updating coffee shop: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )


@router.delete(
    "/{shop_id}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
    summary="Delete coffee shop",
)
def delete_shop(
    shop_id: UUID,
    _current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
) -> MessageResponse:
    """Delete an existing coffee shop record by ID."""
    try:
        result = supabase.table("shops").delete().eq("id", str(shop_id)).execute()
        if not result.data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found.",
            )
        return MessageResponse(message="Coffee shop deleted successfully.")
    except APIError as exc:
        logger.error(f"Database error deleting coffee shop {shop_id}: {exc.message}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="A database error occurred while deleting the coffee shop.",
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Unexpected error deleting coffee shop: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while processing the request.",
        )
