from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict


class FavoriteStatusResponse(BaseModel):
    """Schema representing the favorite status of a coffee shop for the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: UUID
    is_favorite: bool
    favorited_at: Optional[datetime] = None
