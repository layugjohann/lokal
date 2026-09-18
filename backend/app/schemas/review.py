from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReviewSource(str, Enum):
    """Enumeration of supported review sources."""
    GOOGLE = "google"
    LOKAL = "lokal"


class ReviewAuthor(BaseModel):
    """Author attribution details for a review."""
    model_config = ConfigDict(from_attributes=True)

    display_name: str = Field(..., description="Public display name of the reviewer")
    avatar_url: Optional[str] = Field(None, description="URL of reviewer's avatar image")
    profile_url: Optional[str] = Field(None, description="URL to reviewer's public profile")


class UnifiedReview(BaseModel):
    """Provider-neutral representation of a coffee shop review."""
    model_config = ConfigDict(from_attributes=True)

    id: str = Field(..., description="Provider-neutral unique review identifier")
    source: ReviewSource = Field(..., description="Originating source of the review")
    rating: float = Field(..., ge=1, le=5, description="Review rating from 1 to 5 stars")
    text: Optional[str] = Field(None, description="Review body text (localized)")
    original_text: Optional[str] = Field(None, description="Original untranslated review body text")
    language: Optional[str] = Field(None, description="Language code of the review text")
    author: ReviewAuthor = Field(..., description="Reviewer profile and attribution details")
    published_at: Optional[datetime] = Field(None, description="Original publication timestamp")
    updated_at: Optional[datetime] = Field(None, description="Timestamp of the latest edit, if modified")
    is_edited: bool = Field(False, description="Whether the review has been edited after publication")
    relative_time: Optional[str] = Field(None, description="Human-readable relative time description")
    report_url: Optional[str] = Field(None, description="URL to report or flag review content")


class ReviewCreate(BaseModel):
    """Payload schema for creating a LOKAL first-party user review."""
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    content: Optional[str] = Field(None, max_length=1000, description="Optional review text (max 1000 characters)")

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            trimmed = v.strip()
            return trimmed if trimmed else None
        return v


class ReviewUpdate(BaseModel):
    """Payload schema for partially updating an existing LOKAL user review."""
    rating: Optional[int] = Field(None, ge=1, le=5, description="Updated star rating (1-5)")
    content: Optional[str] = Field(None, max_length=1000, description="Updated review text (max 1000 characters)")

    @field_validator("rating", mode="before")
    @classmethod
    def validate_rating(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("Rating cannot be null or cleared.")
        return v

    @field_validator("content", mode="before")
    @classmethod
    def normalize_content(cls, v: Any) -> Optional[str]:
        if isinstance(v, str):
            trimmed = v.strip()
            return trimmed if trimmed else None
        return v


class ProviderAttribution(BaseModel):
    """Provider-mandated attribution and source metadata."""
    model_config = ConfigDict(from_attributes=True)

    provider: ReviewSource = Field(..., description="Source provider identifier")
    display_name: str = Field(..., description="Provider display label, e.g. 'Google Maps'")
    source_url: Optional[str] = Field(None, description="Direct URL to shop's place page on provider")
    required_notice: str = Field(..., description="Required legal display notice")


class ShopReviewsResponse(BaseModel):
    """Response payload containing normalized reviews and provider attribution."""
    model_config = ConfigDict(from_attributes=True)

    shop_id: Union[UUID, str] = Field(..., description="LOKAL coffee shop identifier")
    average_rating: Optional[float] = Field(None, description="Aggregated rating from external provider")
    total_reviews_count: Optional[int] = Field(None, description="Total count of reviews on external provider")
    lokal_average_rating: Optional[float] = Field(None, description="Aggregated rating from LOKAL community reviews")
    lokal_reviews_count: int = Field(0, description="Total count of LOKAL community reviews")
    reviews: list[UnifiedReview] = Field(default_factory=list, description="List of normalized reviews")
    attributions: list[ProviderAttribution] = Field(default_factory=list, description="Provider attribution items")
    has_more: bool = Field(False, description="Whether additional reviews can be paginated")
