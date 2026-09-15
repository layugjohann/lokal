from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator


class ShopBase(BaseModel):

    """Base schema with common coffee shop fields and validation."""
    name: str = Field(..., min_length=1, max_length=255, description="Name of the coffee shop")
    address: Optional[str] = Field(None, max_length=500, description="Physical address of the coffee shop")
    latitude: float = Field(..., ge=-90.0, le=90.0, description="Latitude coordinate between -90.0 and 90.0")
    longitude: float = Field(..., ge=-180.0, le=180.0, description="Longitude coordinate between -180.0 and 180.0")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Average rating between 0.00 and 5.00")
    google_place_id: Optional[str] = Field(None, max_length=255, description="Google Places ID for external integration")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate and strip leading/trailing whitespace from coffee shop name."""
        v = v.strip()
        if not v:
            raise ValueError("Coffee shop name cannot be empty or whitespace.")
        return v

    @field_validator("address", "google_place_id")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        """Strip optional text fields and normalize empty strings to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class ShopCreate(ShopBase):
    """Payload for creating a new coffee shop."""
    pass


class ShopUpdate(BaseModel):
    """Payload for updating an existing coffee shop (partial update)."""
    name: Optional[str] = Field(None, min_length=1, max_length=255, description="Name of the coffee shop")
    address: Optional[str] = Field(None, max_length=500, description="Physical address of the coffee shop")
    latitude: Optional[float] = Field(None, ge=-90.0, le=90.0, description="Latitude coordinate between -90.0 and 90.0")
    longitude: Optional[float] = Field(None, ge=-180.0, le=180.0, description="Longitude coordinate between -180.0 and 180.0")
    rating: Optional[float] = Field(None, ge=0.0, le=5.0, description="Average rating between 0.00 and 5.00")
    google_place_id: Optional[str] = Field(None, max_length=255, description="Google Places ID for external integration")

    @field_validator("name", "latitude", "longitude", mode="before")
    @classmethod
    def reject_explicit_null(cls, v: Any, info: ValidationInfo) -> Any:
        """Reject explicit null values for required non-nullable fields."""
        if v is None:
            raise ValueError(f"{info.field_name.capitalize()} cannot be null.")
        return v

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        """Validate and strip leading/trailing whitespace from coffee shop name if provided."""
        if v is not None:
            v = v.strip()
            if not v:
                raise ValueError("Coffee shop name cannot be empty or whitespace.")
        return v

    @field_validator("address", "google_place_id")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        """Strip optional text fields and normalize empty strings to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None



class ShopResponse(BaseModel):

    """Response representation of a coffee shop."""
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str] = Field(..., description="Unique coffee shop identifier (UUID)")
    name: str = Field(..., description="Name of the coffee shop")
    address: Optional[str] = Field(None, description="Physical address of the coffee shop")
    latitude: float = Field(..., description="Latitude coordinate")
    longitude: float = Field(..., description="Longitude coordinate")
    rating: Optional[float] = Field(None, description="Average rating")
    google_place_id: Optional[str] = Field(None, description="Google Places identifier")
    created_at: Optional[Union[datetime, str]] = Field(None, description="Creation timestamp")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="Last update timestamp")
