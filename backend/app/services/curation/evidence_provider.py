import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional
import httpx

from ...core.config import settings
from .deduplicator import CandidatePlace

logger = logging.getLogger(__name__)

GOOGLE_PLACES_TEXT_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
TEXT_SEARCH_FIELD_MASK = "places.id,places.displayName,places.formattedAddress,nextPageToken"


class ExternalProviderError(Exception):
    """Raised when an external evidence provider request fails."""
    pass


@dataclass(frozen=True)
class ProviderSearchResult:
    """Result of an evidence search query from an external provider."""
    places: list[CandidatePlace]
    next_page_token: Optional[str]
    has_more: bool


class BaseEvidenceProvider(ABC):
    """Abstract interface for external business location evidence providers."""

    @abstractmethod
    async def search_locations(
        self, query: str, page_token: Optional[str] = None
    ) -> ProviderSearchResult:
        """Search for business locations matching the query.

        Args:
            query: The search query string (e.g. brand name + business category).
            page_token: Optional token for retrieving subsequent pages.

        Returns:
            ProviderSearchResult with candidate places and pagination info.

        Raises:
            ExternalProviderError: If the request fails or provider returns an error.
        """
        pass


class GooglePlacesEvidenceProvider(BaseEvidenceProvider):
    """Evidence provider implementing Google Places API (New) Text Search."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 6.0) -> None:
        self.api_key = settings.GOOGLE_PLACES_API_KEY if api_key is None else api_key
        self.timeout = timeout

    async def search_locations(
        self, query: str, page_token: Optional[str] = None
    ) -> ProviderSearchResult:
        """Search for business locations using Google Places API (New) Text Search."""
        if not self.api_key:
            logger.error("GOOGLE_PLACES_API_KEY is not configured for evidence provider.")
            raise ExternalProviderError("Google Places API key is not configured.")

        headers = {
            "Content-Type": "application/json",
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": TEXT_SEARCH_FIELD_MASK,
        }

        payload: dict[str, str] = {"textQuery": query}
        if page_token:
            payload["pageToken"] = page_token

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    GOOGLE_PLACES_TEXT_SEARCH_URL,
                    headers=headers,
                    json=payload,
                )

            if response.status_code == 404:
                return ProviderSearchResult(places=[], next_page_token=None, has_more=False)

            if response.status_code != 200:
                logger.warning(
                    f"Google Places Text Search failed with HTTP {response.status_code}: {response.text}"
                )
                raise ExternalProviderError(
                    f"Google Places API returned HTTP {response.status_code}"
                )

            try:
                data = response.json()
                if not isinstance(data, dict):
                    raise ValueError("Provider response body is not a JSON object.")
                raw_places = data.get("places", [])
                if not isinstance(raw_places, list):
                    raise ValueError("'places' field in provider response is not a list.")

                next_token: Optional[str] = None
                if "nextPageToken" in data and data["nextPageToken"] is not None:
                    raw_token = data["nextPageToken"]
                    if not isinstance(raw_token, str) or not raw_token.strip():
                        raise ValueError(
                            "Provider returned malformed 'nextPageToken': must be a non-empty string when present."
                        )
                    next_token = raw_token.strip()

                candidate_places: list[CandidatePlace] = []
                for item in raw_places:
                    if not isinstance(item, dict):
                        continue
                    place_id = item.get("id")
                    if not place_id or not isinstance(place_id, str):
                        continue

                    display_name_obj = item.get("displayName")
                    display_name = ""
                    if isinstance(display_name_obj, dict):
                        display_name = str(display_name_obj.get("text", "") or "")
                    formatted_address = item.get("formattedAddress")
                    if formatted_address is not None and not isinstance(formatted_address, str):
                        formatted_address = str(formatted_address)

                    candidate_places.append(
                        CandidatePlace(
                            place_id=place_id,
                            display_name=display_name,
                            formatted_address=formatted_address,
                        )
                    )

                return ProviderSearchResult(
                    places=candidate_places,
                    next_page_token=next_token,
                    has_more=bool(next_token),
                )
            except (ValueError, TypeError, KeyError, AttributeError) as exc:
                logger.warning(f"Google Places Text Search returned malformed response: {exc}")
                raise ExternalProviderError(
                    "Google Places API returned an invalid response."
                ) from exc

        except httpx.RequestError as exc:
            logger.error(f"Network error querying Google Places Text Search for '{query}': {exc}")
            raise ExternalProviderError(
                f"Failed to communicate with Google Places API: {exc}"
            ) from exc
