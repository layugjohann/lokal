from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field
from .shop import NearbyShopResponse


class RecommendationStatus(str, Enum):
    PERSONALIZED = "personalized"
    INSUFFICIENT_DATA = "insufficient_data"
    EMPTY = "empty"


class RecommendedShopItem(BaseModel):
    shop: NearbyShopResponse
    explanation: str


class PersonalizedRecommendationsResponse(BaseModel):
    status: RecommendationStatus
    message: Optional[str] = None
    recommendations: list[RecommendedShopItem] = Field(default_factory=list)
    total_candidates_evaluated: int = 0


class CandidateEvidencePack(BaseModel):
    shop_id: str
    shop_name: str
    matched_feature_label: Optional[str] = None
    lokal_community_rating: Optional[float] = None


class StructuredAIExplanation(BaseModel):
    matched_feature: Optional[str] = Field(
        None,
        description="The exact matched feature label from the evidence pack",
    )
    explanation: str = Field(
        ...,
        min_length=15,
        max_length=200,
        description="Concise location-independent explanation connecting user taste to shop evidence",
    )
