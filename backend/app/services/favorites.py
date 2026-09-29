from datetime import datetime
import logging
from typing import Any, Optional, Union
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ..schemas.auth import UserResponse
from ..schemas.favorite import FavoriteStatusResponse

logger = logging.getLogger(__name__)


def _parse_timestamp(val: Any) -> Optional[datetime]:
    """Parse a datetime object or ISO string timestamp safely."""
    if isinstance(val, datetime):
        return val
    if isinstance(val, str) and val.strip():
        try:
            return datetime.fromisoformat(val.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


class FavoriteService:
    """Service layer managing coffee shop favorites for authenticated users."""

    def _get_shop_curation_status(self, shop_id: str, supabase: Client) -> str:
        """Retrieve the curation status of a shop. Defaults to PENDING_REVIEW (fail-closed)."""
        try:
            curation_res = (
                supabase.table("shop_curation")
                .select("status")
                .eq("shop_id", shop_id)
                .execute()
            )
            if curation_res.data:
                return curation_res.data[0].get("status", "PENDING_REVIEW")
            return "PENDING_REVIEW"
        except Exception as exc:
            logger.warning(f"Failed to fetch curation status for shop {shop_id}: {exc}")
            return "PENDING_REVIEW"

    def get_favorite_status(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        supabase: Client,
    ) -> FavoriteStatusResponse:
        """Retrieve whether the current authenticated user has favorited an approved coffee shop.

        Returns 404 Not Found if the shop does not exist or is not approved.
        """
        str_shop_id = str(shop_id)

        # 1. Verify shop existence
        try:
            shop_res = supabase.table("shops").select("id").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying the coffee shop.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error checking shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

        # 2. Enforce fail-closed shop curation status
        curation_status = self._get_shop_curation_status(str_shop_id, supabase)
        if curation_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Coffee shop not found or is not approved for public discovery.",
            )

        # 3. Query caller's favorite state
        try:
            res = (
                supabase.table("favorites")
                .select("id, created_at")
                .eq("shop_id", str_shop_id)
                .eq("user_id", user.id)
                .execute()
            )
            if res.data:
                row = res.data[0]
                return FavoriteStatusResponse(
                    shop_id=UUID(str_shop_id),
                    is_favorite=True,
                    favorited_at=_parse_timestamp(row.get("created_at")),
                )
            return FavoriteStatusResponse(
                shop_id=UUID(str_shop_id),
                is_favorite=False,
                favorited_at=None,
            )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking favorite status for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving favorite status.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error retrieving favorite status for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def add_favorite(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        supabase: Client,
    ) -> FavoriteStatusResponse:
        """Add a coffee shop to the authenticated user's favorites.

        Enforces coffee shop existence, APPROVED curation status, and uniqueness.
        """
        str_shop_id = str(shop_id)

        # 1. Verify shop existence
        try:
            shop_res = supabase.table("shops").select("id").eq("id", str_shop_id).execute()
            if not shop_res.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error checking shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying the coffee shop.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error checking shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

        # 2. Enforce APPROVED shop curation status
        curation_status = self._get_shop_curation_status(str_shop_id, supabase)
        if curation_status != "APPROVED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot favorite a coffee shop that is not approved for public discovery.",
            )

        # 3. Call secure PostgreSQL RPC create_user_favorite
        rpc_params = {
            "p_shop_id": str_shop_id,
        }

        try:
            result = supabase.rpc("create_user_favorite", rpc_params).execute()
            if not result.data:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to persist favorite record.",
                )
            row = result.data if isinstance(result.data, dict) else result.data[0]
            return FavoriteStatusResponse(
                shop_id=UUID(str_shop_id),
                is_favorite=True,
                favorited_at=_parse_timestamp(row.get("created_at")),
            )
        except APIError as exc:
            logger.warning(f"Database error adding favorite for shop {shop_id}: {exc.message}")
            if exc.code == "23505" or "already favorited" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="You have already favorited this coffee shop.",
                )
            if exc.code == "P0001" or "not approved" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Cannot favorite a coffee shop that is not approved for public discovery.",
                )
            if exc.code == "P0002" or "not found" in (exc.message or ""):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop not found.",
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while saving your favorite.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error adding favorite for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

    def remove_favorite(
        self,
        shop_id: Union[UUID, str],
        user: UserResponse,
        supabase: Client,
    ) -> None:
        """Remove a coffee shop from the authenticated user's favorites.

        Permitted even if the shop is currently EXCLUDED or PENDING_REVIEW,
        preserving caller data ownership.
        """
        str_shop_id = str(shop_id)

        try:
            existing = (
                supabase.table("favorites")
                .select("id")
                .eq("shop_id", str_shop_id)
                .eq("user_id", user.id)
                .execute()
            )
            if not existing.data:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Coffee shop is not in your favorites.",
                )

            supabase.table("favorites").delete().eq("shop_id", str_shop_id).eq("user_id", user.id).execute()
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error deleting favorite for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while removing your favorite.",
            )
        except Exception as exc:
            logger.error(f"Unexpected error deleting favorite for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )
