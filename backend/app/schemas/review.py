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


class SummaryStatus(str, Enum):
    """Status indicator for coffee shop review summaries."""
    AVAILABLE = "available"
    INSUFFICIENT_REVIEWS = "insufficient_reviews"


class ReviewInput(BaseModel):
    """Sanitized review input for the summarizer with author/PII excluded."""
    rating: float = Field(..., ge=1, le=5, description="Star rating (1 to 5)")
    text: str = Field(..., min_length=1, description="Sanitized non-empty review text")


class ReviewSummaryContent(BaseModel):
    """Structured synthesis generated by the review summarizer."""
    summary: str = Field(
        ...,
        min_length=10,
        max_length=600,
        description="Concise overall synthesis of customer reviews",
    )
    positive_themes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Recurring positive themes across reviews (max 5)",
    )
    negative_themes: list[str] = Field(
        default_factory=list,
        max_length=5,
        description="Recurring negative themes or areas for improvement (max 5)",
    )


class ShopReviewSummaryResponse(BaseModel):
    """API response schema for coffee shop review summary."""
    model_config = ConfigDict(from_attributes=True)

    shop_id: Union[UUID, str] = Field(..., description="LOKAL coffee shop identifier")
    status: SummaryStatus = Field(..., description="Availability status of the review summary")
    summary: Optional[str] = Field(None, description="Concise overall review synthesis")
    positive_themes: list[str] = Field(
        default_factory=list,
        description="Recurring positive highlights across customer feedback",
    )
    negative_themes: list[str] = Field(
        default_factory=list,
        description="Recurring negative highlights or areas for improvement",
    )
    review_count_analyzed: int = Field(
        0, description="Total count of usable text reviews analyzed"
    )


class RecommendationStatus(str, Enum):
    """Availability status indicator for coffee shop recommendations."""
    AVAILABLE = "available"
    INSUFFICIENT_REVIEWS = "insufficient_reviews"


class RecommendationItem(BaseModel):
    """Public recommendation item presented to users."""
    model_config = ConfigDict(from_attributes=True)

    item_name: str = Field(
        ...,
        min_length=2,
        max_length=60,
        description="Specific menu, coffee, or food item name",
    )
    reason: str = Field(
        ...,
        min_length=10,
        max_length=300,
        description="Concise evidence-based reason derived from positive review mentions",
    )


class ShopRecommendationsResponse(BaseModel):
    """API response schema for coffee shop recommendations."""
    model_config = ConfigDict(from_attributes=True)

    shop_id: Union[UUID, str] = Field(..., description="LOKAL coffee shop identifier")
    status: RecommendationStatus = Field(..., description="Recommendation availability status")
    items: list[RecommendationItem] = Field(
        default_factory=list,
        description="List of positively recommended menu items",
    )
    review_count_analyzed: int = Field(
        0, description="Total count of usable text reviews analyzed"
    )

