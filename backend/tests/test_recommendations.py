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

from app.api.deps import get_authenticated_supabase, get_current_user
from app.api.v1.endpoints.reviews import (
    get_review_recommendation_service,
    get_review_service,
)
from app.core.config import settings
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.review import (
    ProviderAttribution,
    RecommendationItem,
    RecommendationStatus,
    ReviewAuthor,
    ReviewCreate,
    ReviewInput,
    ReviewSource,
    ReviewUpdate,
    ShopRecommendationsResponse,
    ShopReviewsResponse,
    UnifiedReview,
)
from app.services.reviews.base import ExternalProviderError
from app.services.reviews.recommendations import (
    GEMINI_API_BASE_URL,
    InternalRecommendationContent,
    InternalRecommendationItem,
    InMemoryRecommendationCache,
    GeminiReviewRecommender,
    ReviewRecommendationService,
    get_recommendation_cache,
    validate_and_convert_recommendations,
)
from app.services.reviews.service import ReviewService


class TestGroundingValidator(unittest.TestCase):
    """Unit tests for the 5-point server-side grounding validator."""

    def setUp(self) -> None:
        self.sample_reviews = [
            ReviewInput(rating=5.0, text="The spanish latte is incredible and super smooth!"),
            ReviewInput(rating=5.0, text="Overall 5 stars! But avoid the burnt bagel."),
            ReviewInput(rating=3.0, text="The cold brew was decent, nothing special."),
            ReviewInput(rating=4.5, text="Loved the pistachio croissant, perfectly flaky."),
            ReviewInput(rating=5.0, text="Great atmosphere! Don't get the iced americano though."),
            ReviewInput(rating=5.0, text="Top notch espresso, but skip the bitter matcha."),
        ]

    def test_valid_positive_evidence_excerpt(self) -> None:
        """Valid positive evidence with exact excerpt, rating >= 4, and no negative signals succeeds."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Spanish Latte",
                    reason="Customers love the rich and smooth flavor.",
                    supporting_review_index=0,
                    supporting_evidence="The spanish latte is incredible and super smooth!",
                ),
                InternalRecommendationItem(
                    item_name="Pistachio Croissant",
                    reason="Praised for its flaky layers and pistachio taste.",
                    supporting_review_index=3,
                    supporting_evidence="Loved the pistachio croissant, perfectly flaky.",
                ),
            ]
        )

        result = validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].item_name, "Spanish Latte")
        self.assertEqual(result[0].reason, "Customers love the rich and smooth flavor.")
        self.assertEqual(result[1].item_name, "Pistachio Croissant")
        self.assertEqual(result[1].reason, "Praised for its flaky layers and pistachio taste.")

    def test_evidence_excerpt_not_present_in_source_review(self) -> None:
        """Excerpt string not present in cited review fails validation."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Spanish Latte",
                    reason="Great drink.",
                    supporting_review_index=0,
                    supporting_evidence="This exact sentence is completely fabricated!",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("not present in referenced review", str(ctx.exception))

    def test_evidence_excerpt_from_wrong_review(self) -> None:
        """Excerpt belonging to review at index 3 cited with index 0 fails validation."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Pistachio Croissant",
                    reason="Flaky pastry.",
                    supporting_review_index=0,  # Actually from review index 3
                    supporting_evidence="Loved the pistachio croissant, perfectly flaky.",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("not present in referenced review", str(ctx.exception))

    def test_item_present_in_review_but_absent_from_evidence_excerpt(self) -> None:
        """Excerpt from the review that does not contain the item name fails validation."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Spanish Latte",
                    reason="Good review.",
                    supporting_review_index=0,
                    # Review text has 'spanish latte', but excerpt cites an unrelated part:
                    supporting_evidence="incredible and super smooth!",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("does not occur in supporting evidence", str(ctx.exception))

    def test_high_rated_review_with_negative_mention_avoid_burnt_bagel(self) -> None:
        """5-star review containing 'avoid the burnt bagel' is rejected by negative-context guard."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Bagel",
                    reason="Customer mentioned the bagel.",
                    supporting_review_index=1,  # 5-star review
                    supporting_evidence="avoid the burnt bagel",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("negative context in evidence", str(ctx.exception))

    def test_representative_negative_contexts_rejected(self) -> None:
        """Obvious negative indicators (skip, don't get, bitter, terrible) are rejected."""
        test_cases = [
            (5, "Matcha", "skip the bitter matcha", "skip"),
            (4, "Iced Americano", "Don't get the iced americano though", "don't get"),
        ]
        for idx, item, evidence, expected_token in test_cases:
            internal = InternalRecommendationContent(
                items=[
                    InternalRecommendationItem(
                        item_name=item,
                        reason="Negative mention.",
                        supporting_review_index=idx,
                        supporting_evidence=evidence,
                    )
                ]
            )
            with self.assertRaises(ExternalProviderError) as ctx:
                validate_and_convert_recommendations(internal, self.sample_reviews)
            self.assertIn("negative context in evidence", str(ctx.exception))

    def test_referenced_review_rating_below_four_rejected(self) -> None:
        """Referencing a 3-star review (rating < 4.0) fails validation."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Cold Brew",
                    reason="Decent cold brew.",
                    supporting_review_index=2,  # Rating is 3.0
                    supporting_evidence="The cold brew was decent, nothing special.",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("non-positive review", str(ctx.exception))

    def test_out_of_bounds_index_rejected(self) -> None:
        """Out-of-bounds review index fails validation."""
        internal = InternalRecommendationContent(
            items=[
                InternalRecommendationItem(
                    item_name="Latte",
                    reason="Good latte.",
                    supporting_review_index=99,
                    supporting_evidence="some text",
                )
            ]
        )
        with self.assertRaises(ExternalProviderError) as ctx:
            validate_and_convert_recommendations(internal, self.sample_reviews)
        self.assertIn("out-of-bounds", str(ctx.exception))


class TestGeminiReviewRecommender(unittest.IsolatedAsyncioTestCase):
    """Unit tests for GeminiReviewRecommender provider calls and error handling."""

    def setUp(self) -> None:
        self.api_key = "test-gemini-key"
        self.model = "gemini-2.5-flash"
        self.recommender = GeminiReviewRecommender(
            api_key=self.api_key,
            model=self.model,
            timeout=5.0,
        )
        self.sample_reviews = [
            ReviewInput(rating=5.0, text="The iced spanish latte is rich and creamy!"),
            ReviewInput(rating=4.5, text="Best sea salt latte in town, loved it."),
            ReviewInput(rating=5.0, text="Try the blueberry scone with your coffee."),
        ]

    async def test_recommend_success(self) -> None:
        expected_json = json.dumps({
            "items": [
                {
                    "item_name": "Spanish Latte",
                    "reason": "Reviewers love its rich and creamy texture.",
                    "supporting_review_index": 0,
                    "supporting_evidence": "The iced spanish latte is rich and creamy!",
                }
            ]
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
            items = await self.recommender.recommend(self.sample_reviews)

            self.assertEqual(len(items), 1)
            self.assertEqual(items[0].item_name, "Spanish Latte")
            self.assertEqual(
                items[0].reason, "Reviewers love its rich and creamy texture."
            )

    async def test_thinking_budget_configured_for_gemini_2_5(self) -> None:
        expected_json = json.dumps({"items": []})
        mock_response_data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": expected_json}]},
                    "finishReason": "STOP",
                }
            ]
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            await self.recommender.recommend(self.sample_reviews)

            called_kwargs = mock_post.call_args[1]
            body = called_kwargs["json"]
            self.assertIn("thinkingConfig", body["generationConfig"])
            self.assertEqual(
                body["generationConfig"]["thinkingConfig"]["thinkingBudget"], 0
            )

    async def test_missing_api_key_raises_external_provider_error(self) -> None:
        recommender = GeminiReviewRecommender(api_key=None)
        with patch.object(settings, "GEMINI_API_KEY", None):
            recommender.api_key = None
            with self.assertRaises(ExternalProviderError) as ctx:
                await recommender.recommend(self.sample_reviews)
            self.assertIn("not configured", str(ctx.exception))

    async def test_non_stop_finish_reason_raises_error(self) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": json.dumps({"items": []})}]},
                    "finishReason": "MAX_TOKENS",
                }
            ]
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.recommender.recommend(self.sample_reviews)
            self.assertIn("finishReason=MAX_TOKENS", str(ctx.exception))

    async def test_http_429_rate_limit(self) -> None:
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 429
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.recommender.recommend(self.sample_reviews)
            self.assertIn("rate limit exceeded", str(ctx.exception))

    async def test_network_timeout(self) -> None:
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.side_effect = httpx.TimeoutException("Connection timed out")
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.recommender.recommend(self.sample_reviews)
            self.assertIn("timed out", str(ctx.exception))

    async def test_malformed_json_response(self) -> None:
        mock_response_data = {
            "candidates": [
                {
                    "content": {"parts": [{"text": "Not a valid JSON string"}]},
                    "finishReason": "STOP",
                }
            ]
        }
        mock_response = MagicMock(spec=httpx.Response)
        mock_response.status_code = 200
        mock_response.json.return_value = mock_response_data

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            with self.assertRaises(ExternalProviderError) as ctx:
                await self.recommender.recommend(self.sample_reviews)
            self.assertIn("expected recommendation schema", str(ctx.exception))


class TestInMemoryRecommendationCache(unittest.TestCase):
    """Unit tests for InMemoryRecommendationCache generation tracking and TTL."""

    def setUp(self) -> None:
        self.cache = InMemoryRecommendationCache(ttl_seconds=3600.0, max_capacity=3)

    def test_set_and_get(self) -> None:
        items = [RecommendationItem(item_name="Spanish Latte", reason="Smooth and sweet.")]
        self.cache.set("shop-1", items, 3)

        cached = self.cache.get("shop-1")
        self.assertIsNotNone(cached)
        cached_items, count = cached
        self.assertEqual(len(cached_items), 1)
        self.assertEqual(cached_items[0].item_name, "Spanish Latte")
        self.assertEqual(count, 3)

    def test_ttl_expiration(self) -> None:
        items = [RecommendationItem(item_name="Spanish Latte", reason="Smooth and sweet.")]
        self.cache.set("shop-1", items, 3)

        with patch("time.time", return_value=time.time() + 3601.0):
            cached = self.cache.get("shop-1")
            self.assertIsNone(cached)

    def test_capacity_eviction_oldest(self) -> None:
        items = [RecommendationItem(item_name="Espresso", reason="Bold and punchy.")]
        self.cache.set("shop-1", items, 3)
        time.sleep(0.01)
        self.cache.set("shop-2", items, 4)
        time.sleep(0.01)
        self.cache.set("shop-3", items, 5)
        time.sleep(0.01)
        # Adding a 4th entry exceeds capacity 3, should evict shop-1 (oldest)
        self.cache.set("shop-4", items, 6)

        self.assertIsNone(self.cache.get("shop-1"))
        self.assertIsNotNone(self.cache.get("shop-2"))
        self.assertIsNotNone(self.cache.get("shop-3"))
        self.assertIsNotNone(self.cache.get("shop-4"))

    def test_set_if_generation_guard(self) -> None:
        items = [RecommendationItem(item_name="Mocha", reason="Chocolatey and warm.")]
        gen1 = self.cache.get_generation("shop-1")

        # Invalidate shop-1 while generation was in-flight
        self.cache.invalidate("shop-1")

        # Attempt to write with stale generation
        stored = self.cache.set_if_generation("shop-1", items, 3, gen1)
        self.assertFalse(stored)
        self.assertIsNone(self.cache.get("shop-1"))

    def test_invalidate_and_clear(self) -> None:
        items = [RecommendationItem(item_name="Latte", reason="Milky coffee.")]
        self.cache.set("shop-1", items, 3)
        self.cache.set("shop-2", items, 4)

        self.cache.invalidate("shop-1")
        self.assertIsNone(self.cache.get("shop-1"))
        self.assertIsNotNone(self.cache.get("shop-2"))

        self.cache.clear()
        self.assertIsNone(self.cache.get("shop-2"))


class TestReviewRecommendationService(unittest.IsolatedAsyncioTestCase):
    """Integration tests for ReviewRecommendationService business logic."""

    def setUp(self) -> None:
        self.shop_id = uuid4()
        self.mock_supabase = MagicMock()
        self.mock_recommender = MagicMock(spec=GeminiReviewRecommender)
        self.cache = InMemoryRecommendationCache()
        self.service = ReviewRecommendationService(
            recommender=self.mock_recommender,
            cache=self.cache,
        )

        self.mock_review_service = MagicMock(spec=ReviewService)
        self.mock_review_service._get_shop_curation_status.return_value = "APPROVED"

    async def test_get_shop_recommendations_cache_hit(self) -> None:
        items = [RecommendationItem(item_name="Spanish Latte", reason="Loved by regulars.")]
        self.cache.set(str(self.shop_id), items, 5)

        res = await self.service.get_shop_recommendations(
            shop_id=self.shop_id,
            supabase=self.mock_supabase,
            review_service=self.mock_review_service,
        )

        self.assertEqual(res.status, RecommendationStatus.AVAILABLE)
        self.assertEqual(len(res.items), 1)
        self.assertEqual(res.items[0].item_name, "Spanish Latte")
        self.assertEqual(res.review_count_analyzed, 5)
        # Should not fetch reviews or call recommender on cache hit
        self.mock_review_service.get_shop_reviews.assert_not_called()
        self.mock_recommender.recommend.assert_not_called()

    async def test_insufficient_reviews_returns_status_and_skips_ai(self) -> None:
        # Shop with only 2 reviews (< 3 threshold)
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id="r1",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text="Good coffee.",
                        author=ReviewAuthor(display_name="User 1"),
                    ),
                    UnifiedReview(
                        id="r2",
                        source=ReviewSource.LOKAL,
                        rating=4.0,
                        text="Nice atmosphere.",
                        author=ReviewAuthor(display_name="User 2"),
                    ),
                ],
                attributions=[],
                has_more=False,
            )
        )

        res = await self.service.get_shop_recommendations(
            shop_id=self.shop_id,
            supabase=self.mock_supabase,
            review_service=self.mock_review_service,
        )

        self.assertEqual(res.status, RecommendationStatus.INSUFFICIENT_REVIEWS)
        self.assertEqual(res.items, [])
        self.assertEqual(res.review_count_analyzed, 2)
        self.mock_recommender.recommend.assert_not_called()

    async def test_empty_reviews_filtered_out(self) -> None:
        # 3 reviews, but 2 are rating-only (empty/whitespace text)
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id="r1",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text="Great place!",
                        author=ReviewAuthor(display_name="User 1"),
                    ),
                    UnifiedReview(
                        id="r2",
                        source=ReviewSource.LOKAL,
                        rating=4.0,
                        text=None,
                        author=ReviewAuthor(display_name="User 2"),
                    ),
                    UnifiedReview(
                        id="r3",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text="   ",
                        author=ReviewAuthor(display_name="User 3"),
                    ),
                ],
                attributions=[],
                has_more=False,
            )
        )

        res = await self.service.get_shop_recommendations(
            shop_id=self.shop_id,
            supabase=self.mock_supabase,
            review_service=self.mock_review_service,
        )

        self.assertEqual(res.status, RecommendationStatus.INSUFFICIENT_REVIEWS)
        self.assertEqual(res.review_count_analyzed, 1)
        self.mock_recommender.recommend.assert_not_called()

    async def test_three_plus_reviews_no_items_returns_available_empty(self) -> None:
        # 3 usable reviews, but recommender found no recommended items
        self.mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id=f"r{i}",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text=f"Review text {i} about wifi and seating.",
                        author=ReviewAuthor(display_name=f"User {i}"),
                    )
                    for i in range(3)
                ],
                attributions=[],
                has_more=False,
            )
        )
        self.mock_recommender.recommend = AsyncMock(return_value=[])

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            res = await self.service.get_shop_recommendations(
                shop_id=self.shop_id,
                supabase=self.mock_supabase,
                review_service=self.mock_review_service,
            )

        self.assertEqual(res.status, RecommendationStatus.AVAILABLE)
        self.assertEqual(res.items, [])
        self.assertEqual(res.review_count_analyzed, 3)


class TestRecommendationsEndpoint(unittest.TestCase):
    """End-to-end endpoint tests for GET /api/v1/shops/{shop_id}/reviews/recommendations."""

    def setUp(self) -> None:
        self.client = TestClient(app)
        self.shop_id = uuid4()
        self.test_user = UserResponse(
            id=str(uuid4()),
            email="tester@lokal.ph",
            display_name="Tester",
            role="authenticated",
        )
        self.mock_supabase = MagicMock()
        get_recommendation_cache().clear()

    def tearDown(self) -> None:
        app.dependency_overrides.clear()
        get_recommendation_cache().clear()

    def test_unauthenticated_request_returns_401(self) -> None:
        app.dependency_overrides.clear()
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/recommendations"
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_non_approved_shop_returns_404(self) -> None:
        mock_review_service = MagicMock(spec=ReviewService)
        mock_review_service._get_shop_curation_status.return_value = "EXCLUDED"

        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_review_service] = lambda: mock_review_service

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/recommendations"
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_authenticated_approved_shop_returns_recommendations(self) -> None:
        mock_review_service = MagicMock(spec=ReviewService)
        mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id=f"r{i}",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text=f"The sea salt latte {i} is fantastic!",
                        author=ReviewAuthor(display_name=f"User {i}"),
                    )
                    for i in range(3)
                ],
                attributions=[],
                has_more=False,
            )
        )

        mock_recommender = MagicMock(spec=GeminiReviewRecommender)
        mock_recommender.recommend = AsyncMock(
            return_value=[
                RecommendationItem(
                    item_name="Sea Salt Latte",
                    reason="Consistently praised for its rich and balanced flavor.",
                )
            ]
        )

        mock_rec_service = ReviewRecommendationService(
            recommender=mock_recommender,
            cache=get_recommendation_cache(),
        )

        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        app.dependency_overrides[get_review_recommendation_service] = lambda: mock_rec_service

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            response = self.client.get(
                f"/api/v1/shops/{self.shop_id}/reviews/recommendations"
            )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"], "available")
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["item_name"], "Sea Salt Latte")
        self.assertEqual(data["review_count_analyzed"], 3)

    def test_unconfigured_gemini_api_key_returns_503(self) -> None:
        mock_review_service = MagicMock(spec=ReviewService)
        mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id=f"r{i}",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text=f"Great coffee {i}",
                        author=ReviewAuthor(display_name=f"User {i}"),
                    )
                    for i in range(3)
                ],
                attributions=[],
                has_more=False,
            )
        )

        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        app.dependency_overrides[get_review_recommendation_service] = (
            lambda: ReviewRecommendationService(cache=get_recommendation_cache())
        )

        with patch.object(settings, "GEMINI_API_KEY", None):
            response = self.client.get(
                f"/api/v1/shops/{self.shop_id}/reviews/recommendations"
            )

        self.assertEqual(response.status_code, status.HTTP_503_SERVICE_UNAVAILABLE)
        self.assertIn("not configured", response.json()["detail"])

    def test_ai_provider_failure_returns_502(self) -> None:
        mock_review_service = MagicMock(spec=ReviewService)
        mock_review_service._get_shop_curation_status.return_value = "APPROVED"
        mock_review_service.get_shop_reviews = AsyncMock(
            return_value=ShopReviewsResponse(
                shop_id=self.shop_id,
                reviews=[
                    UnifiedReview(
                        id=f"r{i}",
                        source=ReviewSource.LOKAL,
                        rating=5.0,
                        text=f"Great coffee {i}",
                        author=ReviewAuthor(display_name=f"User {i}"),
                    )
                    for i in range(3)
                ],
                attributions=[],
                has_more=False,
            )
        )

        mock_recommender = MagicMock(spec=GeminiReviewRecommender)
        mock_recommender.recommend = AsyncMock(
            side_effect=ExternalProviderError("Gemini timed out.")
        )
        mock_rec_service = ReviewRecommendationService(
            recommender=mock_recommender,
            cache=get_recommendation_cache(),
        )

        app.dependency_overrides[get_current_user] = lambda: self.test_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_review_service] = lambda: mock_review_service
        app.dependency_overrides[get_review_recommendation_service] = lambda: mock_rec_service

        with patch.object(settings, "GEMINI_API_KEY", "valid-key"):
            response = self.client.get(
                f"/api/v1/shops/{self.shop_id}/reviews/recommendations"
            )

        self.assertEqual(response.status_code, status.HTTP_502_BAD_GATEWAY)
        self.assertIn("temporarily unavailable", response.json()["detail"])


class TestMutationCacheInvalidation(unittest.TestCase):
    """Verify that review mutations (create, update, delete) invalidate the recommendation cache."""

    def setUp(self) -> None:
        self.review_service = ReviewService()
        self.shop_id = uuid4()
        self.user = UserResponse(
            id=str(uuid4()),
            email="mutator@lokal.ph",
            display_name="Mutator",
            role="authenticated",
        )
        self.mock_supabase = MagicMock()
        self.review_service._get_shop_curation_status = MagicMock(return_value="APPROVED")
        get_recommendation_cache().clear()

    def tearDown(self) -> None:
        get_recommendation_cache().clear()

    def test_create_user_review_invalidates_recommendation_cache(self) -> None:
        cache = get_recommendation_cache()
        items = [RecommendationItem(item_name="Spanish Latte", reason="Loved by all.")]
        cache.set(str(self.shop_id), items, 3)
        self.assertIsNotNone(cache.get(str(self.shop_id)))

        # Mock successful RPC call
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[
                {
                    "id": "rev-1",
                    "rating": 5,
                    "content": "New review",
                    "author_name": "Mutator",
                    "source": "lokal",
                    "created_at": "2026-09-29T00:00:00Z",
                    "updated_at": "2026-09-29T00:00:00Z",
                }
            ]
        )
        self.mock_supabase.rpc.return_value = mock_rpc

        self.review_service.create_user_review(
            shop_id=self.shop_id,
            user=self.user,
            review_in=ReviewCreate(rating=5, content="New review"),
            supabase=self.mock_supabase,
        )

        self.assertIsNone(cache.get(str(self.shop_id)))

    def test_update_user_review_invalidates_recommendation_cache(self) -> None:
        cache = get_recommendation_cache()
        items = [RecommendationItem(item_name="Spanish Latte", reason="Loved by all.")]
        cache.set(str(self.shop_id), items, 3)
        self.assertIsNotNone(cache.get(str(self.shop_id)))

        # Mock shop check, curation check, review existence, and update RPC
        mock_shops = MagicMock()
        mock_shops.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": str(self.shop_id)}]
        )
        mock_curation = MagicMock()
        mock_curation.select.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"status": "APPROVED"}]
        )
        mock_existing = MagicMock()
        mock_existing.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "rev-1"}]
        )

        def table_router(name: str):
            if name == "shops":
                return mock_shops
            if name == "shop_curation":
                return mock_curation
            if name == "reviews":
                return mock_existing
            return MagicMock()

        self.mock_supabase.table.side_effect = table_router

        mock_rpc = MagicMock()
        mock_rpc.execute.return_value = MagicMock(
            data=[
                {
                    "id": "rev-1",
                    "rating": 4,
                    "content": "Updated review",
                    "author_name": "Mutator",
                    "source": "lokal",
                    "created_at": "2026-09-29T00:00:00Z",
                    "updated_at": "2026-09-29T01:00:00Z",
                }
            ]
        )
        self.mock_supabase.rpc.return_value = mock_rpc

        self.review_service.update_user_review(
            shop_id=self.shop_id,
            user=self.user,
            review_in=ReviewUpdate(rating=4, content="Updated review"),
            supabase=self.mock_supabase,
        )

        self.assertIsNone(cache.get(str(self.shop_id)))

    def test_delete_user_review_invalidates_recommendation_cache(self) -> None:
        cache = get_recommendation_cache()
        items = [RecommendationItem(item_name="Spanish Latte", reason="Loved by all.")]
        cache.set(str(self.shop_id), items, 3)
        self.assertIsNotNone(cache.get(str(self.shop_id)))

        mock_existing = MagicMock()
        mock_existing.select.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock(
            data=[{"id": "rev-1"}]
        )
        mock_existing.delete.return_value.eq.return_value.eq.return_value.eq.return_value.execute.return_value = MagicMock()

        self.mock_supabase.table.return_value = mock_existing

        self.review_service.delete_user_review(
            shop_id=self.shop_id,
            user=self.user,
            supabase=self.mock_supabase,
        )

        self.assertIsNone(cache.get(str(self.shop_id)))

