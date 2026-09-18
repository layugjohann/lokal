from datetime import datetime
from enum import Enum
from typing import Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator


class ShopEligibilityStatus(str, Enum):
    """Eligibility status of a coffee shop business."""
    APPROVED = "APPROVED"
    EXCLUDED = "EXCLUDED"
    PENDING_REVIEW = "PENDING_REVIEW"


class CurationConfidence(str, Enum):
    """Confidence level of the curation decision."""
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class ShopCurationResponse(BaseModel):
    """Response representation of a coffee shop's curation and eligibility record."""
    model_config = ConfigDict(from_attributes=True)

    shop_id: Union[UUID, str] = Field(..., description="Unique coffee shop identifier")
    status: ShopEligibilityStatus = Field(..., description="Current eligibility status")
    location_count: Optional[int] = Field(None, ge=0, description="Determined number of qualifying physical locations")
    evidence_source: Optional[str] = Field(None, description="Source of classification evidence")
    confidence: CurationConfidence = Field(default=CurationConfidence.LOW, description="Confidence of the decision")
    is_manual_override: bool = Field(default=False, description="Whether status was set via manual curator override")
    curator_id: Optional[Union[UUID, str]] = Field(None, description="Identifier of the curator who performed manual override")
    curator_notes: Optional[str] = Field(None, description="Notes or explanation for the curation decision")
    evaluated_at: Optional[Union[datetime, str]] = Field(None, description="Timestamp of the most recent evaluation")
    created_at: Optional[Union[datetime, str]] = Field(None, description="Record creation timestamp")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="Record last update timestamp")


class CurationOverrideRequest(BaseModel):
    """Payload for an authorized curator to override a shop's eligibility status."""
    status: ShopEligibilityStatus = Field(..., description="Target status: APPROVED or EXCLUDED")
    reason: str = Field(..., min_length=1, max_length=1000, description="Mandatory justification for the manual override")

    @field_validator("status")
    @classmethod
    def validate_target_status(cls, v: ShopEligibilityStatus) -> ShopEligibilityStatus:
        if v == ShopEligibilityStatus.PENDING_REVIEW:
            raise ValueError("Manual override must designate shop as APPROVED or EXCLUDED.")
        return v

    @field_validator("reason")
    @classmethod
    def validate_reason(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("A non-empty reason is required for manual curation overrides.")
        return v


class CurationEvaluationResponse(BaseModel):
    """Response payload returned when an evaluation run completes."""
    shop_id: Union[UUID, str] = Field(..., description="Unique coffee shop identifier")
    status: ShopEligibilityStatus = Field(..., description="Resulting eligibility status")
    location_count: Optional[int] = Field(None, ge=0, description="Determined number of qualifying physical locations")
    evidence_source: Optional[str] = Field(None, description="Source of classification evidence")
    confidence: CurationConfidence = Field(..., description="Confidence of the decision")
    is_manual_override: bool = Field(default=False, description="Whether status remains locked under manual override")
    evaluated_at: Optional[Union[datetime, str]] = Field(None, description="Timestamp of the evaluation")
    message: str = Field(..., description="Summary of the evaluation outcome")
