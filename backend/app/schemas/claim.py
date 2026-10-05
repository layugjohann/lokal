from datetime import datetime
from enum import Enum
from typing import Any, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .shop import ShopResponse


class ShopClaimStatus(str, Enum):
    """Enumeration of possible coffee shop ownership claim statuses."""
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVOKED = "REVOKED"


class ClaimCreate(BaseModel):
    """Payload for submitting a coffee shop ownership claim."""
    claimant_name: str = Field(..., min_length=2, max_length=100, description="Full name of the claimant")
    claimant_phone: Optional[str] = Field(None, max_length=50, description="Contact phone number")
    claimant_role: str = Field(..., min_length=2, max_length=100, description="Role or position at the coffee shop (e.g., Owner, Store Manager)")
    business_proof: Optional[str] = Field(None, max_length=1000, description="Optional verification details, notes, or reference IDs")

    @field_validator("claimant_name", "claimant_role")
    @classmethod
    def validate_required_text(cls, v: str) -> str:
        """Strip whitespace and reject blank input."""
        v = v.strip()
        if not v:
            raise ValueError("Field cannot be empty or whitespace.")
        return v

    @field_validator("claimant_phone", "business_proof")
    @classmethod
    def validate_optional_text(cls, v: Optional[str]) -> Optional[str]:
        """Strip optional text and normalize empty strings to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class ClaimReviewRequest(BaseModel):
    """Payload for curator review decisions (approve, reject, revoke)."""
    review_notes: Optional[str] = Field(None, max_length=1000, description="Optional curator notes or reason for decision")

    @field_validator("review_notes")
    @classmethod
    def validate_notes(cls, v: Optional[str]) -> Optional[str]:
        """Strip whitespace and normalize empty strings to None."""
        if v is not None:
            v = v.strip()
            return v if v else None
        return None


class ShopClaimResponse(BaseModel):
    """User-facing response representation of a coffee shop claim.

    Strictly omits internal user_id, claimant phone, and business proof to minimize
    unnecessary data exposure.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str] = Field(..., description="Unique claim identifier")
    shop_id: Union[UUID, str] = Field(..., description="Target coffee shop identifier")
    status: ShopClaimStatus = Field(..., description="Current status of the claim")
    claimant_name: str = Field(..., description="Claimant name")
    claimant_role: str = Field(..., description="Claimant role/title")
    rejection_reason: Optional[str] = Field(None, description="Explanation if claim was rejected or revoked")
    created_at: Union[datetime, str] = Field(..., description="Submission timestamp")
    updated_at: Union[datetime, str] = Field(..., description="Last update timestamp")

    @model_validator(mode="before")
    @classmethod
    def derive_rejection_reason(cls, data: Any) -> Any:
        """Derive user-facing rejection_reason from internal review_notes for REJECTED and REVOKED claims."""
        if isinstance(data, dict):
            status = data.get("status")
            status_str = status.value if hasattr(status, "value") else str(status) if status is not None else ""
            if status_str in ("REJECTED", "REVOKED"):
                if not data.get("rejection_reason"):
                    data = {**data, "rejection_reason": data.get("review_notes")}
            elif status_str in ("PENDING", "APPROVED"):
                if data.get("rejection_reason"):
                    data = {**data, "rejection_reason": None}
        return data


class ShopClaimDetailResponse(ShopClaimResponse):
    """Curator-facing detailed response representation of a claim including internal audit data."""
    user_id: Union[UUID, str] = Field(..., description="Claimant auth user ID")
    claimant_phone: Optional[str] = Field(None, description="Claimant contact phone")
    business_proof: Optional[str] = Field(None, description="Submitted proof/verification notes")
    curator_id: Optional[Union[UUID, str]] = Field(None, description="Curator reviewer ID")
    review_notes: Optional[str] = Field(None, description="Curator review notes")
    reviewed_at: Optional[Union[datetime, str]] = Field(None, description="Review decision timestamp")
    shop: Optional[ShopResponse] = Field(None, description="Associated coffee shop details")
