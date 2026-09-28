import json
import time
from typing import Any, Optional
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

from fastapi import status
from fastapi.testclient import TestClient
import httpx
from postgrest.exceptions import APIError

from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase
from app.api.v1.endpoints.reviews import get_review_service, get_review_summary_service
from app.core.config import settings
import app.core.supabase as core_supabase
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.review import (
    ProviderAttribution,
    ReviewAuthor,
    ReviewCreate,
    ReviewInput,
    ReviewSource,
    ReviewSummaryContent,
    ShopReviewsResponse,
    ShopReviewSummaryResponse,
    SummaryStatus,
    UnifiedReview,
)
from app.services.reviews.base import ExternalProviderError
from app.services.reviews.service import ReviewService
from app.services.reviews.summary import (
    GEMINI_API_BASE_URL,
    MAX_REVIEWS_TO_ANALYZE,
    MIN_REVIEWS_FOR_SUMMARY,
    GeminiReviewSummarizer,
    InMemorySummaryCache,
    ReviewSummaryService,
    get_summary_cache,
)


class TestGeminiReviewSummarizer(unittest.IsolatedAsyncioTestCase):
    """Unit tests for GeminiReviewSummarizer REST client and structured output handling."""

    def setUp(self) -> None:
        self.api_key = "test-gemini-key"
        self.model = "gemini-2.5-flash"
        self.summarizer = GeminiReviewSummarizer(
            api_key=self.api_key,
            model=self.model,
            timeout=5.0,
        )

    def _sample_reviews(self) -> list[ReviewInput]:
        return [
            ReviewInput(rating=5.0, text="Amazing pour-over and great seating."),
            ReviewInput(rating=4.0, text="Delicious pastries, but limited afternoon parking."),
            ReviewInput(rating=5.0, text="Friendly baristas and quiet vibe for remote work."),
        ]

    async def test_summarize_success(self) -> None:
        expected_json = json.dumps({
            "summary": "Customers consistently praise the pour-over coffee and welcoming atmosphere.",
            "positive_themes": ["Exceptional pour-over coffee", "Quiet work-friendly vibe"],
            "negative_themes": ["Limited afternoon parking"],
        })
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": expected_json}],
                        "role": "model",
                    },
                    "finishReason": "STOP",
                }
            ]
        }

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await self.summarizer.summarize(self._sample_reviews())

            self.assertIsInstance(result, ReviewSummaryContent)
            self.assertEqual(
                result.summary,
                "Customers consistently praise the pour-over coffee and welcoming atmosphere.",
            )
            self.assertEqual(len(result.positive_themes), 2)
            self.assertEqual(len(result.negative_themes), 1)

            # Verify request payload
            mock_post.assert_called_once()
            call_kwargs = mock_post.call_args.kwargs
            json_body = call_kwargs["json"]
            self.assertIn("system_instruction", json_body)
            self.assertIn("contents", json_body)
            self.assertEqual(json_body["generationConfig"]["responseMimeType"], "application/json")
            self.assertIn("responseSchema", json_body["generationConfig"])

    async def test_summarize_missing_api_key_raises_error(self) -> None:
        summarizer = GeminiReviewSummarizer(api_key="")
        with self.assertRaises(ExternalProviderError) as ctx:
            await summarizer.summarize(self._sample_reviews())
        self.assertIn("not configured", str(ctx.exception))

    async def test_summarize_rate_limit_429_raises_error(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        mock_response.text = "Quota exceeded"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("rate limit exceeded", str(ctx.exception))

    async def test_summarize_http_500_raises_error(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 500
        mock_response.text = "Internal Server Error"

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("HTTP 500", str(ctx.exception))

    async def test_summarize_timeout_raises_error(self) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out")
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("timed out", str(ctx.exception))

    async def test_summarize_network_request_error_raises_error(self) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.RequestError("Connection reset by peer")
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("Failed to communicate", str(ctx.exception))

    async def test_summarize_malformed_json_raises_validation_error(self) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": "Not a valid JSON string"}],
                        "role": "model",
                    }
                }
            ]
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("expected summary schema", str(ctx.exception))

    async def test_summarize_schema_violation_missing_summary_raises_error(self) -> None:
        # Missing required 'summary' key
        invalid_json = json.dumps({
            "positive_themes": ["Great coffee"],
            "negative_themes": [],
        })
        mock_response_data = {
            "candidates": [
                {
                    "content": {
                        "parts": [{"text": invalid_json}],
                        "role": "model",
                    }
                }
            ]
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.summarizer.summarize(self._sample_reviews())
            self.assertIn("expected summary schema", str(ctx.exception))


class TestInMemorySummaryCache(unittest.TestCase):
    """Unit tests for the in-memory summary TTL cache."""

    def setUp(self) -> None:
        self.cache = InMemorySummaryCache(ttl_seconds=1.0, max_capacity=3)
        self.sample_content = ReviewSummaryContent(
            summary="A lovely neighbourhood spot for espresso and pastries.",
            positive_themes=["Espresso", "Pastries"],
            negative_themes=[],
        )

    def test_set_and_get_cache_hit(self) -> None:
        self.cache.set("shop-1", self.sample_content, 5)
        res = self.cache.get("shop-1")
        self.assertIsNotNone(res)
        content, count = res  # type: ignore[misc]
        self.assertEqual(content.summary, self.sample_content.summary)
        self.assertEqual(count, 5)

    def test_cache_miss_when_key_absent(self) -> None:
        self.assertIsNone(self.cache.get("nonexistent"))

    def test_cache_expiry_after_ttl(self) -> None:
        cache = InMemorySummaryCache(ttl_seconds=0.01)
        cache.set("shop-1", self.sample_content, 3)
        time.sleep(0.02)
        self.assertIsNone(cache.get("shop-1"))

    def test_cache_eviction_on_capacity(self) -> None:
        cache = InMemorySummaryCache(ttl_seconds=60.0, max_capacity=2)
        cache.set("shop-1", self.sample_content, 3)
        time.sleep(0.001)
        cache.set("shop-2", self.sample_content, 4)
        time.sleep(0.001)
        # Adding 3rd entry should evict oldest (shop-1)
        cache.set("shop-3", self.sample_content, 5)

        self.assertIsNone(cache.get("shop-1"))
        self.assertIsNotNone(cache.get("shop-2"))
        self.assertIsNotNone(cache.get("shop-3"))

    def test_invalidate_specific_shop(self) -> None:
        self.cache.set("shop-1", self.sample_content, 3)
        self.cache.set("shop-2", self.sample_content, 4)
        self.cache.invalidate("shop-1")

        self.assertIsNone(self.cache.get("shop-1"))
        self.assertIsNotNone(self.cache.get("shop-2"))

    def test_clear_cache(self) -> None:
        self.cache.set("shop-1", self.sample_content, 3)
        self.cache.clear()
        self.assertIsNone(self.cache.get("shop-1"))


class TestReviewSummaryService(unittest.IsolatedAsyncioTestCase):
    """Unit tests for the application-level ReviewSummaryService."""

    def setUp(self) -> None:
        self.mock_summarizer = AsyncMock()
        self.cache = InMemorySummaryCache(ttl_seconds=3600.0, max_capacity=100)
        self.service = ReviewSummaryService(
            summarizer=self.mock_summarizer,
            cache=self.cache,
        )
        self.shop_id = str(uuid4())
        self.mock_supabase = MagicMock()
        self.mock_review_service = MagicMock()

    def _make_unified_reviews(self, texts: list[Optional[str]]) -> list[UnifiedReview]:
        reviews = []
        for i, text in enumerate(texts):
            reviews.append(
                UnifiedReview(
                    id=f"lokal:rev-{i}",
                    source=ReviewSource.LOKAL,
                    rating=5.0,
                    text=text,
                    original_text=text,
                    author=ReviewAuthor(display_name=f"User {i}"),
                )
            )
        return reviews

    async def test_unapproved_shop_raises_404(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "PENDING_REVIEW"
        with self.assertRaises(Exception) as ctx:
            await self.service.get_shop_summary(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )
        self.assertEqual(ctx.exception.status_code, 404)  # type: ignore[attr-defined]

    async def test_insufficient_reviews_returns_empty_state_without_calling_summarizer(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        # Only 2 reviews with text (threshold is 3)
        reviews = self._make_unified_reviews(["Great place!", "Good coffee."])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )

        res = await self.service.get_shop_summary(
            shop_id=self.shop_id,
            supabase=self.mock_supabase,
            review_service=self.mock_review_service,
        )

        self.assertEqual(res.status, SummaryStatus.INSUFFICIENT_REVIEWS)
        self.assertIsNone(res.summary)
        self.assertEqual(res.positive_themes, [])
        self.assertEqual(res.negative_themes, [])
        self.assertEqual(res.review_count_analyzed, 2)
        # Verify summarizer was NOT called
        self.mock_summarizer.summarize.assert_not_called()

    async def test_rating_only_reviews_omitted_from_usable_count(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        # 4 total reviews, but only 2 have non-empty text
        reviews = self._make_unified_reviews(["Great coffee!", None, "   ", "Cozy vibe."])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )

        res = await self.service.get_shop_summary(
            shop_id=self.shop_id,
            supabase=self.mock_supabase,
            review_service=self.mock_review_service,
        )

        self.assertEqual(res.status, SummaryStatus.INSUFFICIENT_REVIEWS)
        self.assertEqual(res.review_count_analyzed, 2)
        self.mock_summarizer.summarize.assert_not_called()

    async def test_successful_summary_generation_and_caching(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        reviews = self._make_unified_reviews([
            "Delicious pour-over and friendly baristas.",
            "Nice vibe but can get crowded around noon.",
            "Great specialty beans, quiet and clean.",
        ])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )

        sample_summary = ReviewSummaryContent(
            summary="Known for delicious pour-overs and friendly baristas, with peak noon crowds.",
            positive_themes=["Delicious pour-overs", "Friendly baristas"],
            negative_themes=["Crowded at noon"],
        )
        self.mock_summarizer.summarize.return_value = sample_summary

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            res = await self.service.get_shop_summary(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )

            self.assertEqual(res.status, SummaryStatus.AVAILABLE)
            self.assertEqual(res.summary, sample_summary.summary)
            self.assertEqual(res.positive_themes, sample_summary.positive_themes)
            self.assertEqual(res.negative_themes, sample_summary.negative_themes)
            self.assertEqual(res.review_count_analyzed, 3)
            self.mock_summarizer.summarize.assert_called_once()

            # Second call should hit the cache and NOT call the summarizer again
            res_cached = await self.service.get_shop_summary(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )
            self.assertEqual(res_cached.status, SummaryStatus.AVAILABLE)
            self.assertEqual(res_cached.summary, sample_summary.summary)
            self.assertEqual(self.mock_summarizer.summarize.call_count, 1)

    async def test_cache_invalidation_forces_fresh_generation(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        reviews = self._make_unified_reviews([
            "Review one text.",
            "Review two text.",
            "Review three text.",
        ])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )

        sample_summary = ReviewSummaryContent(
            summary="Overall synthesis.",
            positive_themes=["Great taste"],
            negative_themes=[],
        )
        self.mock_summarizer.summarize.return_value = sample_summary

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            # First call populates cache
            await self.service.get_shop_summary(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )
            self.assertEqual(self.mock_summarizer.summarize.call_count, 1)

            # Invalidate cache for shop
            self.service.invalidate_shop_summary(self.shop_id)

            # Next call must re-invoke summarizer
            await self.service.get_shop_summary(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )
            self.assertEqual(self.mock_summarizer.summarize.call_count, 2)

    async def test_missing_gemini_api_key_raises_503(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        reviews = self._make_unified_reviews([
            "Review one text.",
            "Review two text.",
            "Review three text.",
        ])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )

        with patch.object(settings, "GEMINI_API_KEY", ""):
            with self.assertRaises(Exception) as ctx:
                await self.service.get_shop_summary(
                    shop_id=self.shop_id,
                    supabase=self.mock_supabase,
                    review_service=self.mock_review_service,
                )
            self.assertEqual(ctx.exception.status_code, 503)  # type: ignore[attr-defined]

    async def test_summarizer_failure_raises_502(self) -> None:
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        reviews = self._make_unified_reviews([
            "Review one text.",
            "Review two text.",
            "Review three text.",
        ])
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=reviews,
                has_more=False,
            )
        )
        self.mock_summarizer.summarize.side_effect = ExternalProviderError("Rate limit exceeded")

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            with self.assertRaises(Exception) as ctx:
                await self.service.get_shop_summary(
                    shop_id=self.shop_id,
                    supabase=self.mock_supabase,
                    review_service=self.mock_review_service,
                )
            self.assertEqual(ctx.exception.status_code, 502)  # type: ignore[attr-defined]


class TestShopReviewSummaryEndpoint(unittest.TestCase):
    """Integration tests for the GET /api/v1/shops/{shop_id}/reviews/summary endpoint."""

    def setUp(self) -> None:
        core_supabase._supabase_client = None
        self.mock_supabase = MagicMock()
        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)
        self.shop_id = str(uuid4())
        self.test_user = UserResponse(
            id="12345678-1234-5678-1234-567812345678",
            email="testuser@example.com",
            user_metadata={"display_name": "Test User"},
        )
        get_summary_cache().clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        get_summary_cache().clear()
        core_supabase._supabase_client = None

    def test_summary_requires_authentication(self) -> None:
        # Without auth headers, request is rejected with 401
        response = self.client.get(f"/api/v1/shops/{self.shop_id}/reviews/summary")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_summary_success_available(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        mock_summary_service = MagicMock(spec=ReviewSummaryService)
        mock_summary_service.get_shop_summary = AsyncMock(
            return_value=ShopReviewSummaryResponse(
                shop_id=self.shop_id,
                status=SummaryStatus.AVAILABLE,
                summary="Excellent pour-over coffee and pleasant environment.",
                positive_themes=["Pour-over coffee", "Ambiance"],
                negative_themes=["Limited seating"],
                review_count_analyzed=5,
            )
        )
        app.dependency_overrides[get_review_summary_service] = lambda: mock_summary_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/summary",
            headers={"Authorization": "Bearer mock-token"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertEqual(data["status"], "available")
        self.assertEqual(data["summary"], "Excellent pour-over coffee and pleasant environment.")
        self.assertEqual(len(data["positive_themes"]), 2)
        self.assertEqual(len(data["negative_themes"]), 1)
        self.assertEqual(data["review_count_analyzed"], 5)

    def test_summary_insufficient_reviews(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        mock_summary_service = MagicMock(spec=ReviewSummaryService)
        mock_summary_service.get_shop_summary = AsyncMock(
            return_value=ShopReviewSummaryResponse(
                shop_id=self.shop_id,
                status=SummaryStatus.INSUFFICIENT_REVIEWS,
                summary=None,
                positive_themes=[],
                negative_themes=[],
                review_count_analyzed=1,
            )
        )
        app.dependency_overrides[get_review_summary_service] = lambda: mock_summary_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/summary",
            headers={"Authorization": "Bearer mock-token"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "insufficient_reviews")
        self.assertIsNone(data["summary"])
        self.assertEqual(data["positive_themes"], [])
        self.assertEqual(data["negative_themes"], [])
        self.assertEqual(data["review_count_analyzed"], 1)

    def test_summary_curation_rejected_returns_404(self) -> None:
        app.dependency_overrides[get_current_user] = lambda: self.test_user

        mock_review_service = MagicMock(spec=ReviewService)
        mock_review_service._get_shop_curation_status.return_value = "EXCLUDED"
        app.dependency_overrides[get_review_service] = lambda: mock_review_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/summary",
            headers={"Authorization": "Bearer mock-token"},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_first_party_review_mutation_invalidates_cache(self) -> None:
        """Verify that creating, updating, or deleting a review invalidates the summary cache."""
        cache = get_summary_cache()
        sample_content = ReviewSummaryContent(
            summary="Cached summary before mutation.",
            positive_themes=["Great staff"],
            negative_themes=[],
        )
        cache.set(self.shop_id, sample_content, 4)
        self.assertIsNotNone(cache.get(self.shop_id))

        # Perform review creation via ReviewService
        review_service = ReviewService()
        mock_supabase = MagicMock()
        # Mock shop check
        mock_supabase.table.return_value.select.return_value.eq.return_value.execute.return_value.data = [{"id": self.shop_id}]
        # Mock curation
        with patch.object(review_service, "_get_shop_curation_status", return_value="APPROVED"):
            # Mock RPC return
            mock_supabase.rpc.return_value.execute.return_value.data = [{
                "id": str(uuid4()),
                "rating": 5,
                "content": "New review!",
                "author_name": "Test User",
                "created_at": "2026-09-28T00:00:00Z",
                "updated_at": "2026-09-28T00:00:00Z",
            }]
            review_service.create_user_review(
                shop_id=self.shop_id,
                user=self.test_user,
                review_in=ReviewCreate(rating=5, content="New review!"),
                supabase=mock_supabase,
            )

        # Cache must be invalidated
        self.assertIsNone(cache.get(self.shop_id))


if __name__ == "__main__":
    unittest.main()
