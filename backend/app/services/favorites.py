from datetime import datetime
import logging
from typing import Any, Optional, Union
from uuid import UUID
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ..schemas.auth import UserResponse
from ..schemas.favorite import FavoriteShopResponse, FavoriteStatusResponse
from .personalized_cache import get_personalized_cache

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
        """Retrieve the curation status of a shop. Defaults to PENDING_REVIEW when missing (fail-closed).

        Raises:
            HTTPException: 500 if a database or unexpected error occurs.
        """
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
        except APIError as exc:
            logger.error(f"Database error fetching curation status for shop {shop_id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying coffee shop curation status.",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error fetching curation status for shop {shop_id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            ) from exc

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
            get_personalized_cache().invalidate_user(str(user.id))
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
            get_personalized_cache().invalidate_user(str(user.id))
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

    def list_favorites(
        self,
        user: UserResponse,
        supabase: Client,
    ) -> list[FavoriteShopResponse]:
        """Retrieve all approved coffee shops favorited by the authenticated user,

        ordered by most-recently favorited first.
        Non-approved shops (PENDING_REVIEW, EXCLUDED) are excluded.
        """
        # 1. Query user's favorites ordered by created_at DESC
        try:
            fav_res = (
                supabase.table("favorites")
                .select("id, shop_id, created_at")
                .eq("user_id", str(user.id))
                .order("created_at", desc=True)
                .execute()
            )
            favorites_data = fav_res.data or []
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error querying favorites for user {user.id}: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving favorites.",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error querying favorites for user {user.id}: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            ) from exc

        if not favorites_data:
            return []

        shop_ids = [str(item["shop_id"]) for item in favorites_data if item.get("shop_id")]
        if not shop_ids:
            return []

        # 2. Enforce fail-closed shop curation status: filter by APPROVED
        try:
            curation_res = (
                supabase.table("shop_curation")
                .select("shop_id, status")
                .in_("shop_id", shop_ids)
                .eq("status", "APPROVED")
                .execute()
            )
            curation_data = curation_res.data or []
            approved_shop_ids = {str(item["shop_id"]) for item in curation_data if item.get("shop_id")}
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error verifying curation for favorite shops: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while verifying coffee shop curation status.",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error verifying curation for favorite shops: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            ) from exc

        if not approved_shop_ids:
            return []

        # 3. Load corresponding shop records
        try:
            shops_res = (
                supabase.table("shops")
                .select("id, name, address, latitude, longitude, rating, google_place_id, created_at, updated_at")
                .in_("id", list(approved_shop_ids))
                .execute()
            )
            shops_data = shops_res.data or []
            shop_map = {str(s["id"]): s for s in shops_data if s.get("id")}
        except HTTPException:
            raise
        except APIError as exc:
            logger.error(f"Database error retrieving shops for favorites: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving favorite shops.",
            ) from exc
        except Exception as exc:
            logger.error(f"Unexpected error retrieving shops for favorites: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            ) from exc

        # 4. Return all currently approved favorite shops in most-recently-favorited order
        results: list[FavoriteShopResponse] = []
        for fav in favorites_data:
            sid = str(fav.get("shop_id"))
            if sid in approved_shop_ids and sid in shop_map:
                s = shop_map[sid]
                results.append(
                    FavoriteShopResponse(
                        id=s["id"],
                        name=s["name"],
                        address=s.get("address"),
                        latitude=s["latitude"],
                        longitude=s["longitude"],
                        rating=s.get("rating"),
                        google_place_id=s.get("google_place_id"),
                        favorited_at=_parse_timestamp(fav.get("created_at")),
                        created_at=s.get("created_at"),
                        updated_at=s.get("updated_at"),
                    )
                )

        return results

