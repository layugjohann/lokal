import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import httpx
from fastapi import HTTPException
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase
from app.api.v1.endpoints.reviews import get_review_service
from app.main import app
from app.schemas.review import (
    ProviderAttribution,
    ReviewAuthor,
    ReviewSource,
    ShopReviewsResponse,
    UnifiedReview,
)
from app.services.reviews.base import ExternalProviderError
from app.services.reviews.google_places import GooglePlacesReviewProvider
from app.services.reviews.service import ReviewService


class DummyUser:
    def __init__(self, user_id="11111111-2222-3333-4444-555555555555", email="test@example.com"):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"full_name": "Test User"}


class DummyUserResponse:
    def __init__(self, user=Ellipsis):
        if user is Ellipsis:
            self.user = DummyUser()
        else:
            self.user = user


class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data
        self.last_eq = None
        self.mock_execute = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = data
        self.mock_execute.return_value = mock_resp

    def select(self, cols="*"):
        return self

    def eq(self, col, val):
        self.last_eq = (col, val)
        return self

    def execute(self):
        return self.mock_execute()


class TestGooglePlacesReviewProvider(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.provider = GooglePlacesReviewProvider(api_key="test-api-key", timeout=2.0)
        self.mock_google_response = {
            "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4",
            "rating": 4.6,
            "userRatingCount": 84,
            "googleMapsUri": "https://maps.google.com/?cid=1023456789",
            "reviews": [
                {
                    "name": "places/ChIJN1t_tDeuEmsRUsoyG83frY4/reviews/ChZDSUhNMG9nS0VJQ0FnSUN6MjhfZlJnEAE",
                    "relativePublishTimeDescription": "1 month ago",
                    "rating": 5,
                    "text": {
                        "text": "Great pour-over coffee and peaceful ambiance.",
                        "languageCode": "en",
                    },
                    "originalText": {
                        "text": "Great pour-over coffee and peaceful ambiance.",
                        "languageCode": "en",
                    },
                    "authorAttribution": {
                        "displayName": "Maria Santos",
                        "uri": "https://www.google.com/maps/contrib/112233",
                        "photoUri": "https://lh3.googleusercontent.com/a/ACg8oc...",
                    },
                    "publishTime": "2026-08-14T03:22:11.123456Z",
                    "flagContentUri": "https://www.google.com/local/review/rap/report?param=xyz",
                }
            ],
        }

    async def test_fetch_reviews_success(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = self.mock_google_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            reviews, attribution, avg_rating, count = await self.provider.fetch_reviews(
                "ChIJN1t_tDeuEmsRUsoyG83frY4"
            )

        self.assertEqual(len(reviews), 1)
        self.assertEqual(avg_rating, 4.6)
        self.assertEqual(count, 84)

        review = reviews[0]
        self.assertEqual(
            review.id,
            "google:places/ChIJN1t_tDeuEmsRUsoyG83frY4/reviews/ChZDSUhNMG9nS0VJQ0FnSUN6MjhfZlJnEAE",
        )
        self.assertEqual(review.source, ReviewSource.GOOGLE)
        self.assertEqual(review.rating, 5)
        self.assertEqual(review.text, "Great pour-over coffee and peaceful ambiance.")
        self.assertEqual(review.language, "en")
        self.assertEqual(review.author.display_name, "Maria Santos")
        self.assertEqual(review.author.profile_url, "https://www.google.com/maps/contrib/112233")
        self.assertEqual(review.author.avatar_url, "https://lh3.googleusercontent.com/a/ACg8oc...")
        self.assertEqual(review.relative_time, "1 month ago")
        self.assertEqual(review.report_url, "https://www.google.com/local/review/rap/report?param=xyz")

        self.assertIsNotNone(attribution)
        self.assertEqual(attribution.provider, ReviewSource.GOOGLE)
        self.assertEqual(attribution.display_name, "Google Maps")
        self.assertEqual(attribution.source_url, "https://maps.google.com/?cid=1023456789")

    async def test_fetch_reviews_404_not_found(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 404

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            reviews, attribution, avg_rating, count = await self.provider.fetch_reviews(
                "non_existent_place_id"
            )

        self.assertEqual(reviews, [])
        self.assertIsNone(attribution)
        self.assertIsNone(avg_rating)
        self.assertIsNone(count)

    async def test_fetch_reviews_500_server_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.provider.fetch_reviews("ChIJN1t_tDeuEmsRUsoyG83frY4")

        self.assertIn("Google Places API returned HTTP 500", str(ctx.exception))

    async def test_fetch_reviews_network_timeout(self):
        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = httpx.ConnectTimeout("Connection timed out")
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.provider.fetch_reviews("ChIJN1t_tDeuEmsRUsoyG83frY4")

        self.assertIn("Failed to communicate with Google Places API", str(ctx.exception))

    async def test_fetch_reviews_missing_api_key(self):
        provider_no_key = GooglePlacesReviewProvider(api_key="", timeout=2.0)
        with patch("app.services.reviews.google_places.settings.GOOGLE_PLACES_API_KEY", ""):
            with self.assertRaises(ExternalProviderError) as ctx:
                await provider_no_key.fetch_reviews("ChIJN1t_tDeuEmsRUsoyG83frY4")

        self.assertIn("Google Places API key is not configured", str(ctx.exception))

    async def test_fetch_reviews_missing_optional_fields(self):
        minimal_response = {
            "reviews": [
                {
                    "name": "places/ChIJxyz/reviews/abc",
                    "rating": 4,
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = minimal_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            reviews, attribution, avg_rating, count = await self.provider.fetch_reviews("ChIJxyz")

        self.assertEqual(len(reviews), 1)
        review = reviews[0]
        self.assertEqual(review.id, "google:places/ChIJxyz/reviews/abc")
        self.assertEqual(review.rating, 4)
        self.assertIsNone(review.text)
        self.assertEqual(review.author.display_name, "Google Reviewer")
        self.assertIsNone(review.author.avatar_url)
        self.assertIsNone(review.author.profile_url)

    async def test_fetch_reviews_malformed_json_raises_external_provider_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.side_effect = ValueError("Expecting value: line 1 column 1 (char 0)")

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.provider.fetch_reviews("ChIJN1t_tDeuEmsRUsoyG83frY4")

        self.assertIn("Google Places API returned an invalid response", str(ctx.exception))

    async def test_fetch_reviews_invalid_schema_raises_external_provider_error(self):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        # Rating out of bounds (rating must be between 1 and 5)
        mock_resp.json.return_value = {
            "reviews": [
                {
                    "name": "places/ChIJxyz/reviews/invalid",
                    "rating": 10,
                }
            ]
        }

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.provider.fetch_reviews("ChIJxyz")

        self.assertIn("Google Places API returned an invalid response", str(ctx.exception))

    async def test_fetch_reviews_fractional_rating_success(self):
        fractional_response = {
            "reviews": [
                {
                    "name": "places/ChIJxyz/reviews/fractional",
                    "rating": 4.5,
                    "text": {"text": "Very good pour-over, nearly perfect."},
                    "authorAttribution": {"displayName": "Coffee Enthusiast"},
                }
            ]
        }
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = fractional_response

        with patch("httpx.AsyncClient.get", new_callable=AsyncMock) as mock_get:
            mock_get.return_value = mock_resp
            reviews, attribution, avg_rating, count = await self.provider.fetch_reviews("ChIJxyz")

        self.assertEqual(len(reviews), 1)
        review = reviews[0]
        self.assertEqual(review.id, "google:places/ChIJxyz/reviews/fractional")
        self.assertEqual(review.rating, 4.5)
        self.assertIsInstance(review.rating, float)
        self.assertEqual(review.text, "Very good pour-over, nearly perfect.")




class TestReviewService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.mock_provider = AsyncMock()
        self.service = ReviewService(provider=self.mock_provider)
        self.mock_supabase = MagicMock()
        self.shop_id = "123e4567-e89b-12d3-a456-426614174000"

    async def test_get_shop_reviews_shop_not_found(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_shop_reviews(self.shop_id, self.mock_supabase)

        self.assertEqual(ctx.exception.status_code, 404)
        self.assertEqual(ctx.exception.detail, "Coffee shop not found.")

    async def test_get_shop_reviews_no_google_place_id(self):
        shop_data = {
            "id": self.shop_id,
            "name": "Local Café",
            "rating": 4.5,
            "google_place_id": None,
        }
        builder = MockQueryBuilder(data=[shop_data])
        self.mock_supabase.table.return_value = builder

        response = await self.service.get_shop_reviews(self.shop_id, self.mock_supabase)
        self.assertEqual(str(response.shop_id), self.shop_id)
        self.assertEqual(response.average_rating, 4.5)
        self.assertEqual(response.total_reviews_count, 0)
        self.assertEqual(response.reviews, [])
        self.assertEqual(response.attributions, [])
        self.assertFalse(response.has_more)
        self.mock_provider.fetch_reviews.assert_not_called()

    async def test_get_shop_reviews_provider_success(self):
        shop_data = {
            "id": self.shop_id,
            "name": "Local Café",
            "rating": 4.5,
            "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        }
        builder = MockQueryBuilder(data=[shop_data])
        self.mock_supabase.table.return_value = builder

        mock_review = UnifiedReview(
            id="google:rev1",
            source=ReviewSource.GOOGLE,
            rating=5,
            text="Delicious coffee!",
            author=ReviewAuthor(display_name="Juan Cruz"),
        )
        mock_attribution = ProviderAttribution(
            provider=ReviewSource.GOOGLE,
            display_name="Google Maps",
            source_url="https://maps.google.com/?cid=123",
            required_notice="Reviews provided by Google Maps",
        )
        self.mock_provider.fetch_reviews.return_value = (
            [mock_review],
            mock_attribution,
            4.8,
            50,
        )

        response = await self.service.get_shop_reviews(self.shop_id, self.mock_supabase)
        self.assertEqual(str(response.shop_id), self.shop_id)
        self.assertEqual(response.average_rating, 4.8)
        self.assertEqual(response.total_reviews_count, 50)
        self.assertEqual(len(response.reviews), 1)
        self.assertEqual(len(response.attributions), 1)
        self.assertEqual(response.attributions[0].display_name, "Google Maps")

    async def test_get_shop_reviews_provider_error_raises_502(self):
        shop_data = {
            "id": self.shop_id,
            "name": "Local Café",
            "rating": 4.5,
            "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        }
        builder = MockQueryBuilder(data=[shop_data])
        self.mock_supabase.table.return_value = builder

        self.mock_provider.fetch_reviews.side_effect = ExternalProviderError("Network timeout")

        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_shop_reviews(self.shop_id, self.mock_supabase)

        self.assertEqual(ctx.exception.status_code, 502)
        self.assertEqual(
            ctx.exception.detail, "External review provider temporarily unavailable."
        )

    async def test_get_shop_reviews_database_api_error_raises_500(self):
        mock_table = MagicMock()
        mock_select = MagicMock()
        mock_eq = MagicMock()
        mock_eq.execute.side_effect = APIError({"message": "DB connection dead", "code": "50000"})
        mock_select.eq.return_value = mock_eq
        mock_table.select.return_value = mock_select
        self.mock_supabase.table.return_value = mock_table

        with self.assertRaises(HTTPException) as ctx:
            await self.service.get_shop_reviews(self.shop_id, self.mock_supabase)

        self.assertEqual(ctx.exception.status_code, 500)
        self.assertEqual(
            ctx.exception.detail, "A database error occurred while retrieving the coffee shop."
        )


class TestReviewEndpoint(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()
        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)
        self.auth_headers = {"Authorization": "Bearer valid-mock-token"}
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()
        self.shop_id = "123e4567-e89b-12d3-a456-426614174000"

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_reviews_missing_auth(self):
        response = self.client.get(f"/api/v1/shops/{self.shop_id}/reviews")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Authentication token is missing.")

    def test_get_reviews_success(self):
        shop_data = {
            "id": self.shop_id,
            "name": "Local Café",
            "rating": 4.6,
            "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
        }
        builder = MockQueryBuilder(data=[shop_data])
        self.mock_supabase.table.return_value = builder

        mock_review = UnifiedReview(
            id="google:rev-123",
            source=ReviewSource.GOOGLE,
            rating=5,
            text="Amazing roast!",
            author=ReviewAuthor(display_name="Elena Gomez"),
        )
        mock_service = AsyncMock()
        mock_service.get_shop_reviews.return_value = ShopReviewsResponse(
            shop_id=self.shop_id,
            average_rating=4.6,
            total_reviews_count=12,
            reviews=[mock_review],
            attributions=[
                ProviderAttribution(
                    provider=ReviewSource.GOOGLE,
                    display_name="Google Maps",
                    source_url="https://maps.google.com/?cid=123",
                    required_notice="Reviews provided by Google Maps",
                )
            ],
            has_more=False,
        )

        app.dependency_overrides[get_review_service] = lambda: mock_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews", headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertEqual(data["average_rating"], 4.6)
        self.assertEqual(data["total_reviews_count"], 12)
        self.assertEqual(len(data["reviews"]), 1)
        self.assertEqual(data["reviews"][0]["author"]["display_name"], "Elena Gomez")
        self.assertEqual(len(data["attributions"]), 1)
        self.assertEqual(data["attributions"][0]["display_name"], "Google Maps")

    def test_get_reviews_shop_not_found(self):
        mock_service = AsyncMock()
        mock_service.get_shop_reviews.side_effect = HTTPException(
            status_code=404, detail="Coffee shop not found."
        )
        app.dependency_overrides[get_review_service] = lambda: mock_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews", headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Coffee shop not found.")

    def test_get_reviews_external_provider_failure_returns_502(self):
        mock_service = AsyncMock()
        mock_service.get_shop_reviews.side_effect = HTTPException(
            status_code=502, detail="External review provider temporarily unavailable."
        )
        app.dependency_overrides[get_review_service] = lambda: mock_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews", headers=self.auth_headers
        )
        self.assertEqual(response.status_code, 502)
        self.assertEqual(
            response.json()["detail"], "External review provider temporarily unavailable."
        )


if __name__ == "__main__":
    unittest.main()
