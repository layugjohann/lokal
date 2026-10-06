import logging
from typing import Any
from fastapi import HTTPException, status
from postgrest.exceptions import APIError
from supabase import Client

from ..schemas.community import CommunityFeedItem, CommunityFeedResponse

logger = logging.getLogger(__name__)

DEFAULT_FEED_LIMIT = 20
MAX_FEED_LIMIT = 50


class CommunityService:
    """Service layer orchestrating community feed retrieval and pagination."""

    def get_community_feed(
        self,
        supabase: Client,
        limit: int = DEFAULT_FEED_LIMIT,
        offset: int = 0,
    ) -> CommunityFeedResponse:
        """Retrieve paginated first-party reviews for approved coffee shops.

        The database RPC fetches up to (limit + 1) rows so `has_more` is authoritatively
        determined by the presence of an extra row without relying on full table counts
        or speculative length comparisons.

        Args:
            supabase: Authenticated request-scoped Supabase client.
            limit: Maximum number of feed items to return (1 to 50).
            offset: Number of feed items to skip (non-negative).

        Returns:
            CommunityFeedResponse containing items, limit, offset, and has_more flag.

        Raises:
            HTTPException: 500 on database communication error.
        """
        # Clamp limit and offset defensively
        bounded_limit = min(max(1, limit), MAX_FEED_LIMIT)
        bounded_offset = max(0, offset)

        rpc_params = {
            "p_limit": bounded_limit,
            "p_offset": bounded_offset,
        }

        try:
            result = supabase.rpc("get_community_feed", rpc_params).execute()
            raw_rows: list[dict[str, Any]] = result.data or []
        except APIError as exc:
            logger.error(f"Database error executing get_community_feed: {exc.message}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="A database error occurred while retrieving the community feed.",
            )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error(f"Unexpected error executing get_community_feed: {exc}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="An unexpected error occurred while processing the request.",
            )

        # Authoritative has_more check: extra (limit + 1) row indicates additional records exist
        has_more = len(raw_rows) > bounded_limit
        page_rows = raw_rows[:bounded_limit]
        items = [CommunityFeedItem.model_validate(row) for row in page_rows]

        return CommunityFeedResponse(
            items=items,
            limit=bounded_limit,
            offset=bounded_offset,
            has_more=has_more,
        )
