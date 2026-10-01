from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

from .shop import ShopResponse


class FavoriteStatusResponse(BaseModel):
    """Schema representing the favorite status of a coffee shop for the authenticated user."""

    model_config = ConfigDict(from_attributes=True)

    shop_id: UUID
    is_favorite: bool
    favorited_at: Optional[datetime] = None


class FavoriteShopResponse(ShopResponse):
    """Response representation of a favorited coffee shop."""

    favorited_at: Optional[datetime] = Field(
        None, description="When the coffee shop was favorited"
    )

