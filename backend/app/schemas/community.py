from datetime import datetime
from typing import Any, Optional, Union
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, model_validator


def _parse_timestamp(val: Any) -> Optional[datetime]:
    """Parse datetime or ISO timestamp string safely."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class CommunityFeedItem(BaseModel):
    """Public representation of a community feed review item.

    Includes application identifiers (id, shop_id) for client keying, deduplication,
    and shop detail navigation, while strictly excluding private user_id, emails,
    claim data, and curator notes.
    """
    model_config = ConfigDict(from_attributes=True)

    id: Union[UUID, str] = Field(..., description="Unique application review identifier")
    shop_id: Union[UUID, str] = Field(..., description="Target coffee shop identifier for navigation")
    shop_name: str = Field(..., description="Name of the coffee shop")
    shop_address: Optional[str] = Field(None, description="Street address of the coffee shop")
    author_name: str = Field(..., description="Public reviewer display name snapshot")
    rating: int = Field(..., ge=1, le=5, description="Star rating from 1 to 5")
    content: Optional[str] = Field(None, description="Review text content")
    created_at: Union[datetime, str] = Field(..., description="Original publication timestamp")
    updated_at: Optional[Union[datetime, str]] = Field(None, description="Latest update timestamp")
    is_edited: bool = Field(False, description="Whether the review was edited after creation")

    @model_validator(mode="before")
    @classmethod
    def compute_is_edited(cls, data: Any) -> Any:
        """Derive is_edited flag if not explicitly provided."""
        if isinstance(data, dict):
            if "is_edited" not in data or data.get("is_edited") is None:
                c_dt = _parse_timestamp(data.get("created_at"))
                u_dt = _parse_timestamp(data.get("updated_at"))
                data = {**data, "is_edited": bool(c_dt and u_dt and u_dt > c_dt)}
        return data


class CommunityFeedResponse(BaseModel):
    """Paginated collection response for the public community feed."""
    model_config = ConfigDict(from_attributes=True)

    items: list[CommunityFeedItem] = Field(default_factory=list, description="Paginated feed items")
    limit: int = Field(..., ge=1, le=50, description="Requested page size limit")
    offset: int = Field(..., ge=0, description="Requested item offset")
    has_more: bool = Field(False, description="Whether more items exist for pagination")
