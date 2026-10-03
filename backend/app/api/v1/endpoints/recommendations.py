import logging
from typing import Annotated, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from supabase import Client

from ...deps import get_authenticated_supabase, get_current_user
from ....schemas.auth import UserResponse
from ....schemas.recommendation import PersonalizedRecommendationsResponse
from ....services.personalized_recommendation_service import (
    PersonalizedRecommendationService,
    get_personalized_recommendation_service,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get(
    "/personalized",
    response_model=PersonalizedRecommendationsResponse,
    status_code=status.HTTP_200_OK,
    summary="Get personalized coffee shop recommendations",
)
async def get_personalized_recommendations(
    current_user: Annotated[UserResponse, Depends(get_current_user)],
    supabase: Annotated[Client, Depends(get_authenticated_supabase)],
    service: Annotated[
        PersonalizedRecommendationService,
        Depends(get_personalized_recommendation_service),
    ],
    latitude: Optional[float] = Query(
        default=None,
        ge=-90.0,
        le=90.0,
        description="Latitude coordinate between -90.0 and 90.0",
    ),
    longitude: Optional[float] = Query(
        default=None,
        ge=-180.0,
        le=180.0,
        description="Longitude coordinate between -180.0 and 180.0",
    ),
    radius: float = Query(
        default=5000.0,
        gt=0.0,
        le=50000.0,
        description="Search radius in meters (max 50,000m)",
    ),
    limit: int = Query(
        default=5,
        ge=1,
        le=5,
        description="Maximum number of recommendations to return (1-5)",
    ),
) -> PersonalizedRecommendationsResponse:
    """Retrieve personalized coffee shop recommendations tailored to the authenticated user's taste."""
    # Coupled coordinate validation
    if (latitude is None and longitude is not None) or (latitude is not None and longitude is None):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Both latitude and longitude must be provided together.",
        )

    return await service.get_personalized_recommendations(
        user=current_user,
        supabase=supabase,
        latitude=latitude,
        longitude=longitude,
        radius=radius,
        limit=limit,
    )
