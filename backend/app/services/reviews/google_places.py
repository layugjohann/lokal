import logging
from datetime import datetime
from typing import Optional, Tuple
import httpx

from ...core.config import settings
from ...schemas.review import (
    ProviderAttribution,
    ReviewAuthor,
    ReviewSource,
    UnifiedReview,
)
from .base import BaseReviewProvider, ExternalProviderError

logger = logging.getLogger(__name__)

GOOGLE_PLACES_API_URL = "https://places.googleapis.com/v1/places"
FIELD_MASK = (
    "reviews.name,"
    "reviews.rating,"
    "reviews.text,"
    "reviews.originalText,"
    "reviews.authorAttribution,"
    "reviews.publishTime,"
    "reviews.flagContentUri,"
    "reviews.relativePublishTimeDescription,"
    "googleMapsUri,"
    "rating,"
    "userRatingCount"
)


class GooglePlacesReviewProvider(BaseReviewProvider):
    """External review provider implementing Google Places API (New) Place Details."""

    def __init__(self, api_key: Optional[str] = None, timeout: float = 5.0) -> None:
        self.api_key = api_key or settings.GOOGLE_PLACES_API_KEY
        self.timeout = timeout

    async def fetch_reviews(
        self, external_id: str
    ) -> Tuple[list[UnifiedReview], Optional[ProviderAttribution], Optional[float], Optional[int]]:
        """Fetch and normalize up to 5 reviews from Google Places API (New).

        Args:
            external_id: Google Place ID (e.g. 'ChIJN1t_tDeuEmsRUsoyG83frY4').

        Returns:
            Tuple of (reviews, attribution, average_rating, user_rating_count).

        Raises:
            ExternalProviderError: If the Google Places API request fails or times out.
        """
        if not self.api_key:
            logger.error("GOOGLE_PLACES_API_KEY is not configured.")
            raise ExternalProviderError("Google Places API key is not configured.")

        url = f"{GOOGLE_PLACES_API_URL}/{external_id}"
        headers = {
            "X-Goog-Api-Key": self.api_key,
            "X-Goog-FieldMask": FIELD_MASK,
        }

        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(url, headers=headers)

            if response.status_code == 404:
                logger.info(f"Place ID '{external_id}' not found in Google Places.")
                return [], None, None, None

            if response.status_code != 200:
                logger.warning(
                    f"Google Places API request failed for '{external_id}' with HTTP {response.status_code}: {response.text}"
                )
                raise ExternalProviderError(
                    f"Google Places API returned HTTP {response.status_code}"
                )

            data = response.json()
            return self._normalize_response(data, external_id)

        except httpx.RequestError as exc:
            logger.error(
                f"Network error communicating with Google Places API for '{external_id}': {exc}"
            )
            raise ExternalProviderError(
                f"Failed to communicate with Google Places API: {exc}"
            ) from exc

    def _normalize_response(
        self, data: dict, external_id: str
    ) -> Tuple[list[UnifiedReview], Optional[ProviderAttribution], Optional[float], Optional[int]]:
        """Normalize raw Google Places API Place Details response into unified review models."""
        raw_reviews = data.get("reviews", [])
        google_maps_uri = data.get("googleMapsUri")
        avg_rating = data.get("rating")
        user_rating_count = data.get("userRatingCount")

        attribution = ProviderAttribution(
            provider=ReviewSource.GOOGLE,
            display_name="Google Maps",
            source_url=google_maps_uri,
            required_notice="Reviews provided by Google Maps",
        )

        normalized_reviews: list[UnifiedReview] = []

        for item in raw_reviews:
            review_name = item.get("name", f"places/{external_id}/reviews/unknown")
            review_id = f"google:{review_name}"
            rating = item.get("rating", 5)

            # Localized text
            text_obj = item.get("text") or {}
            text = text_obj.get("text")
            language = text_obj.get("languageCode")

            # Original text
            orig_text_obj = item.get("originalText") or {}
            orig_text = orig_text_obj.get("text")

            # Author attribution
            author_obj = item.get("authorAttribution") or {}
            author = ReviewAuthor(
                display_name=author_obj.get("displayName") or "Google Reviewer",
                avatar_url=author_obj.get("photoUri"),
                profile_url=author_obj.get("uri"),
            )

            # Timestamp parsing
            publish_time_str = item.get("publishTime")
            published_at = None
            if publish_time_str:
                try:
                    published_at = datetime.fromisoformat(
                        publish_time_str.replace("Z", "+00:00")
                    )
                except ValueError:
                    published_at = None

            relative_time = item.get("relativePublishTimeDescription")
            report_url = item.get("flagContentUri")

            review = UnifiedReview(
                id=review_id,
                source=ReviewSource.GOOGLE,
                rating=rating,
                text=text,
                original_text=orig_text,
                language=language,
                author=author,
                published_at=published_at,
                relative_time=relative_time,
                report_url=report_url,
            )
            normalized_reviews.append(review)

        return normalized_reviews, attribution, avg_rating, user_rating_count
