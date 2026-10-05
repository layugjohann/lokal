from typing import Any, Optional
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from .claim import ShopClaimResponse
from .review import UnifiedReview
from .shop import ShopResponse


class OwnerShopUpdate(BaseModel):
    """Payload for updating an existing coffee shop by its approved owner.

    Strictly permits only safe business fields: 'name' and 'address'.
    Forbids all extra/protected fields (rating, google_place_id, coordinates, curation status)
    at the request-schema boundary.
    """
    model_config = ConfigDict(extra="forbid")

    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the coffee shop")
    address: Optional[str] = Field(None, max_length=500, description="Physical address of the coffee shop")

    @field_validator("name", mode="before")
    @classmethod
    def reject_explicit_null_name(cls, v: Any, info: ValidationInfo) -> Any:
        """Reject explicit null values for name."""
        if v is None and info.field_name == "name":
            raise ValueError("Coffee shop name cannot be null.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and reject blank input if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Coffee shop name cannot be empty or whitespace.")
        return v

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: Optional[str]) -> Optional[str]:
        """Strip optional address and normalize empty string to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class OwnerDashboardResponse(BaseModel):
    """Aggregated dashboard payload for an approved shop owner."""
    model_config = ConfigDict(from_attributes=True)

    shop: ShopResponse = Field(..., description="Claimed coffee shop details")
    claim: ShopClaimResponse = Field(..., description="Active ownership claim information")
    lokal_rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Average rating from LOKAL community reviews")
    lokal_reviews_count: int = Field(0, ge=0, description="Total count of LOKAL community reviews")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Average rating from external provider")
    recent_reviews: list[UnifiedReview] = Field(default_factory=list, description="Recent sanitized community reviews")
