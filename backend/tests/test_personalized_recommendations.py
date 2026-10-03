import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi import status
from fastapi.testclient import TestClient

from app.api.deps import get_authenticated_supabase, get_current_user
from app.api.v1.endpoints.recommendations import get_personalized_recommendation_service
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.recommendation import (
    CandidateEvidencePack,
    PersonalizedRecommendationsResponse,
    RecommendationStatus,
    RecommendedShopItem,
)
from app.services.favorites import FavoriteService
from app.services.personalized_cache import (
    PersonalizedRecommendationCache,
    get_personalized_cache,
)
from app.services.personalized_recommendation_service import (
    COFFEE_FEATURE_ONTOLOGY,
    CANDIDATE_EVALUATION_LIMIT,
    CANDIDATE_OVERFETCH_LIMIT,
    GeminiExplanationGenerator,
    PersonalizedRecommendationService,
    extract_features_from_text,
)
from app.services.reviews.service import ReviewService


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="test@example.com",
        full_name="Coffee Enthusiast",
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"full_name": full_name}


class TestPersonalizedFeatureExtraction(unittest.TestCase):
    """Test suite for ontology text matching and user taste profile construction."""

    def test_extract_features_matching(self):
        text = "I loved their manual brew pour-over, and it was a quiet work space!"
        feats = extract_features_from_text(text)
        self.assertIn("pour_over", feats)
        self.assertIn("quiet_study", feats)
        self.assertNotIn("matcha", feats)

    def test_extract_features_empty_or_none(self):
        self.assertEqual(extract_features_from_text(None), set())
        self.assertEqual(extract_features_from_text(""), set())
        self.assertEqual(extract_features_from_text("   "), set())
        self.assertEqual(extract_features_from_text("Random non-coffee text"), set())


class TestPersonalizedCacheAndInvalidation(unittest.TestCase):
    """Test suite for location-independent explanation cache and mutation invalidation."""

    def setUp(self):
        self.cache = PersonalizedRecommendationCache()
        get_personalized_cache().clear()

    def tearDown(self):
        get_personalized_cache().clear()

    def test_explanation_cache_stores_and_retrieves(self):
        user_id = str(uuid4())
        shop_id = str(uuid4())
        self.assertIsNone(self.cache.get_explanation(user_id, shop_id))

        self.cache.set_explanation(user_id, shop_id, "Recommended for its specialty pour-over.")
        self.assertEqual(
            self.cache.get_explanation(user_id, shop_id),
            "Recommended for its specialty pour-over.",
        )

    def test_explanation_cache_invalidates_on_user_invalidation(self):
        user_id = str(uuid4())
        shop_id1 = str(uuid4())
        shop_id2 = str(uuid4())
        other_user = str(uuid4())

        self.cache.set_explanation(user_id, shop_id1, "Exp 1")
        self.cache.set_explanation(user_id, shop_id2, "Exp 2")
        self.cache.set_explanation(other_user, shop_id1, "Other user exp")

        self.cache.invalidate_user(user_id)
        self.assertIsNone(self.cache.get_explanation(user_id, shop_id1))
        self.assertIsNone(self.cache.get_explanation(user_id, shop_id2))
        self.assertEqual(self.cache.get_explanation(other_user, shop_id1), "Other user exp")

    def test_favorite_service_invalidates_personalized_cache(self):
        mock_supabase = MagicMock()
        fav_service = FavoriteService()
        user = UserResponse(id=str(uuid4()), email="fav@test.com")
        shop_id = str(uuid4())

        # Seed personalized cache
        get_personalized_cache().set_explanation(str(user.id), shop_id, "Test exp")
        self.assertIsNotNone(get_personalized_cache().get_explanation(str(user.id), shop_id))

        # Mock shop check & RPC
        mock_supabase.table().select().eq().execute.return_value.data = [{"id": shop_id, "status": "APPROVED"}]
        mock_supabase.rpc().execute.return_value.data = [{"created_at": "2026-10-01T00:00:00Z"}]

        fav_service.add_favorite(shop_id, user, mock_supabase)
        self.assertIsNone(get_personalized_cache().get_explanation(str(user.id), shop_id))

    def test_review_service_invalidates_personalized_cache(self):
        from app.schemas.review import ReviewCreate
        mock_supabase = MagicMock()
        rev_service = ReviewService()
        user = UserResponse(id=str(uuid4()), email="rev@test.com")
        shop_id = str(uuid4())

        # Seed personalized cache
        get_personalized_cache().set_explanation(str(user.id), shop_id, "Test exp")
        self.assertIsNotNone(get_personalized_cache().get_explanation(str(user.id), shop_id))

        # Mock shop check & RPC
        mock_supabase.table().select().eq().execute.return_value.data = [{"id": shop_id, "status": "APPROVED"}]
        mock_supabase.rpc().execute.return_value.data = [{
            "id": str(uuid4()),
            "rating": 5,
            "content": "Super",
            "author_name": "Test",
            "created_at": "2026-10-01T00:00:00Z",
            "updated_at": "2026-10-01T00:00:00Z",
        }]

        rev_service.create_user_review(shop_id, user, ReviewCreate(rating=5, content="Super"), mock_supabase)
        self.assertIsNone(get_personalized_cache().get_explanation(str(user.id), shop_id))


class TestGeminiExplanationGenerator(unittest.IsolatedAsyncioTestCase):
    """Test suite verifying location-independent explanation synthesis and grounding validation."""

    async def test_proximity_rejection_in_explanation(self):
        generator = GeminiExplanationGenerator(api_key="mock-key")
        evidence = CandidateEvidencePack(
            shop_id=str(uuid4()),
            shop_name="Kape Bar",
            matched_feature_label="pour-over coffee",
            lokal_community_rating=4.8,
        )

        # Mock Gemini response that illegally contains proximity terms
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"matched_feature": "pour-over coffee", "explanation": "Recommended because it is close and only 300 meters away with great pour-over coffee."}'
                            }
                        ]
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generator.generate_explanation(evidence)
            # Must reject because it contains "meters" / "close"
            self.assertIsNone(result)

    async def test_valid_location_independent_explanation(self):
        generator = GeminiExplanationGenerator(api_key="mock-key")
        evidence = CandidateEvidencePack(
            shop_id=str(uuid4()),
            shop_name="Yardstick",
            matched_feature_label="pour-over coffee",
            lokal_community_rating=4.8,
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "candidates": [
                {
                    "content": {
                        "parts": [
                            {
                                "text": '{"matched_feature": "pour-over coffee", "explanation": "Recommended for its praised pour-over coffee, matching your saved preferences."}'
                            }
                        ]
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
            mock_post.return_value = mock_response
            result = await generator.generate_explanation(evidence)
            self.assertEqual(
                result,
                "Recommended for its praised pour-over coffee, matching your saved preferences.",
            )


class TestPersonalizedRecommendationsService(unittest.IsolatedAsyncioTestCase):
    """Test suite covering candidate pipeline, scoring, exclusions, insufficient-data gate, and tie-breaking."""

    def setUp(self):
        get_personalized_cache().clear()
        self.mock_supabase = MagicMock()
        self.service = PersonalizedRecommendationService()
        self.user = UserResponse(id=str(uuid4()), email="user@test.com")

    def tearDown(self):
        get_personalized_cache().clear()

    async def test_insufficient_data_empty_profile(self):
        # User has no favorites and no reviews
        self.mock_supabase.table().select().eq().eq().execute.return_value.data = []
        self.mock_supabase.table().select().eq().execute.return_value.data = []

        res = await self.service.get_personalized_recommendations(
            user=self.user,
            supabase=self.mock_supabase,
            latitude=14.55,
            longitude=121.01,
        )

        self.assertEqual(res.status, RecommendationStatus.INSUFFICIENT_DATA)
        self.assertEqual(res.recommendations, [])

    async def test_insufficient_data_non_matching_reviews(self):
        # User has a positive review, but text contains NO ontology features
        user_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 5, "content": "Just okay, nice."}]
        self.mock_supabase.table().select().eq().eq().execute.return_value.data = user_reviews
        self.mock_supabase.table().select().eq().execute.return_value.data = []

        res = await self.service.get_personalized_recommendations(
            user=self.user,
            supabase=self.mock_supabase,
            latitude=14.55,
            longitude=121.01,
        )

        self.assertEqual(res.status, RecommendationStatus.INSUFFICIENT_DATA)
        self.assertEqual(res.recommendations, [])

    async def test_insufficient_data_negative_only_reviews(self):
        # User only has reviews with rating <= 2.0
        user_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 1, "content": "Burnt espresso, terrible."}]
        self.mock_supabase.table().select().eq().eq().execute.return_value.data = user_reviews
        self.mock_supabase.table().select().eq().execute.return_value.data = []

        res = await self.service.get_personalized_recommendations(
            user=self.user,
            supabase=self.mock_supabase,
            latitude=14.55,
            longitude=121.01,
        )

        self.assertEqual(res.status, RecommendationStatus.INSUFFICIENT_DATA)
        self.assertEqual(res.recommendations, [])

    async def test_exclusion_favorited_and_reviewed_shops(self):
        fav_shop_id = str(uuid4())
        reviewed_shop_id = str(uuid4())
        candidate_shop_id = str(uuid4())

        user_favorites = [{"id": str(uuid4()), "shop_id": fav_shop_id}]
        user_reviews = [
            {"id": str(uuid4()), "shop_id": reviewed_shop_id, "rating": 5, "content": "Super delicious pour-over coffee!"}
        ]

        # Supabase mock setup:
        # 1. user reviews
        # 2. user favorites
        def table_side_effect(table_name):
            mock_table = MagicMock()
            if table_name == "reviews":
                mock_select = MagicMock()
                # If checking candidate reviews
                mock_select.in_().eq().gte().execute.return_value.data = [
                    {"shop_id": candidate_shop_id, "content": "Best pour-over ever!", "rating": 5}
                ]
                # Default query for user reviews
                mock_select.eq().eq().execute.return_value.data = user_reviews
                mock_table.select.return_value = mock_select
            elif table_name == "favorites":
                mock_select = MagicMock()
                mock_select.eq().execute.return_value.data = user_favorites
                mock_table.select.return_value = mock_select
            return mock_table

        self.mock_supabase.table.side_effect = table_side_effect

        # RPC returns candidate shops including the favorited and reviewed ones
        self.mock_supabase.rpc.return_value.execute.return_value.data = [
            {"id": fav_shop_id, "name": "Fav Shop", "latitude": 14.5, "longitude": 121.0, "rating": 4.5, "distance_meters": 100},
            {"id": reviewed_shop_id, "name": "Rev Shop", "latitude": 14.5, "longitude": 121.0, "rating": 4.5, "distance_meters": 200},
            {"id": candidate_shop_id, "name": "Candidate Shop", "latitude": 14.5, "longitude": 121.0, "rating": 4.8, "distance_meters": 300, "lokal_rating": 4.8, "lokal_reviews_count": 5},
        ]

        res = await self.service.get_personalized_recommendations(
            user=self.user,
            supabase=self.mock_supabase,
            latitude=14.55,
            longitude=121.01,
        )

        self.assertEqual(res.status, RecommendationStatus.PERSONALIZED)
        self.assertEqual(len(res.recommendations), 1)
        self.assertEqual(str(res.recommendations[0].shop.id), candidate_shop_id)

    async def test_preference_differentiation(self):
        """User A (pour-over lover) vs User B (pastry lover) receive different top recommendations."""
        shop_pourover_id = str(uuid4())
        shop_pastry_id = str(uuid4())

        candidate_shops = [
            {"id": shop_pourover_id, "name": "Pour-Over Hub", "latitude": 14.5, "longitude": 121.0, "rating": 4.5, "distance_meters": 500, "lokal_rating": 4.5, "lokal_reviews_count": 5},
            {"id": shop_pastry_id, "name": "Bakery Haven", "latitude": 14.5, "longitude": 121.0, "rating": 4.5, "distance_meters": 500, "lokal_rating": 4.5, "lokal_reviews_count": 5},
        ]

        candidate_reviews = [
            {"shop_id": shop_pourover_id, "content": "Specialty pour-over manual brew is wonderful!", "rating": 5},
            {"shop_id": shop_pastry_id, "content": "Flakiest croissant and bakery pastry in town!", "rating": 5},
        ]

        user_a = UserResponse(id=str(uuid4()), email="user_a@test.com")
        user_b = UserResponse(id=str(uuid4()), email="user_b@test.com")

        user_a_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 5, "content": "I live for pour-over coffee!"}]
        user_b_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 5, "content": "Love fresh croissants and pastries!"}]

        # Test User A
        mock_sub_a = MagicMock()
        def table_a(name):
            m = MagicMock()
            if name == "reviews":
                m.select().eq().eq().execute.return_value.data = user_a_reviews
                m.select().in_().eq().gte().execute.return_value.data = candidate_reviews
            elif name == "favorites":
                m.select().eq().execute.return_value.data = []
            return m
        mock_sub_a.table.side_effect = table_a
        mock_sub_a.rpc.return_value.execute.return_value.data = candidate_shops

        res_a = await self.service.get_personalized_recommendations(user=user_a, supabase=mock_sub_a, latitude=14.5, longitude=121.0)
        self.assertEqual(res_a.status, RecommendationStatus.PERSONALIZED)
        self.assertEqual(str(res_a.recommendations[0].shop.id), shop_pourover_id)

        # Test User B
        mock_sub_b = MagicMock()
        def table_b(name):
            m = MagicMock()
            if name == "reviews":
                m.select().eq().eq().execute.return_value.data = user_b_reviews
                m.select().in_().eq().gte().execute.return_value.data = candidate_reviews
            elif name == "favorites":
                m.select().eq().execute.return_value.data = []
            return m
        mock_sub_b.table.side_effect = table_b
        mock_sub_b.rpc.return_value.execute.return_value.data = candidate_shops

        res_b = await self.service.get_personalized_recommendations(user=user_b, supabase=mock_sub_b, latitude=14.5, longitude=121.0)
        self.assertEqual(res_b.status, RecommendationStatus.PERSONALIZED)
        self.assertEqual(str(res_b.recommendations[0].shop.id), shop_pastry_id)

    async def test_moving_location_recalculates_distance_without_stale_explanation_distance(self):
        """Moving to a new location recalculates exact distance_meters, while cached explanation has no stale distance."""
        shop_id = str(uuid4())
        user_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 5, "content": "Love pour-over coffee"}]
        candidate_reviews = [{"shop_id": shop_id, "content": "Specialty pour-over coffee", "rating": 5}]

        # Location 1: 420m away
        mock_sub = MagicMock()
        def table_fn(name):
            m = MagicMock()
            if name == "reviews":
                m.select().eq().eq().execute.return_value.data = user_reviews
                m.select().in_().eq().gte().execute.return_value.data = candidate_reviews
            elif name == "favorites":
                m.select().eq().execute.return_value.data = []
            return m
        mock_sub.table.side_effect = table_fn

        mock_sub.rpc.return_value.execute.return_value.data = [
            {"id": shop_id, "name": "Yardstick", "latitude": 14.55, "longitude": 121.01, "rating": 4.6, "distance_meters": 420.0, "lokal_rating": 4.8, "lokal_reviews_count": 10}
        ]

        res1 = await self.service.get_personalized_recommendations(user=self.user, supabase=mock_sub, latitude=14.55, longitude=121.01)
        self.assertEqual(res1.recommendations[0].shop.distance_meters, 420.0)
        exp1 = res1.recommendations[0].explanation
        # Explanation must be location independent (no distance text)
        self.assertNotIn("420", exp1)
        self.assertNotIn("meter", exp1.lower())

        # Location 2: User moves 2km away (now 2420m away)
        mock_sub.rpc.return_value.execute.return_value.data = [
            {"id": shop_id, "name": "Yardstick", "latitude": 14.55, "longitude": 121.01, "rating": 4.6, "distance_meters": 2420.0, "lokal_rating": 4.8, "lokal_reviews_count": 10}
        ]

        res2 = await self.service.get_personalized_recommendations(user=self.user, supabase=mock_sub, latitude=14.57, longitude=121.03)
        self.assertEqual(res2.recommendations[0].shop.distance_meters, 2420.0)
        # Reused cached explanation has zero stale distance!
        self.assertEqual(res2.recommendations[0].explanation, exp1)


class TestPersonalizedRecommendationsEndpoint(unittest.TestCase):
    """Test suite for HTTP API endpoint authorization, validation, and contracts."""

    def setUp(self):
        get_personalized_cache().clear()
        self.mock_supabase = MagicMock()
        self.user = UserResponse(id=str(uuid4()), email="endpoint@test.com")

        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_current_user] = lambda: self.user

        self.client = TestClient(app)
        self.headers = {"Authorization": "Bearer valid-mock-jwt"}

    def tearDown(self):
        get_personalized_cache().clear()
        app.dependency_overrides.clear()

    def test_unauthorized_access_denied(self):
        # Clear override for get_current_user to test real 401
        app.dependency_overrides.pop(get_current_user, None)
        client = TestClient(app)
        res = client.get("/api/v1/shops/recommendations/personalized")
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_mismatched_coordinates_rejected_with_400(self):
        # Lat provided without lng
        res = self.client.get("/api/v1/shops/recommendations/personalized?latitude=14.55", headers=self.headers)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("Both latitude and longitude must be provided together", res.json()["detail"])

        # Lng provided without lat
        res = self.client.get("/api/v1/shops/recommendations/personalized?longitude=121.01", headers=self.headers)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_endpoint_returns_insufficient_data_for_new_user(self):
        self.mock_supabase.table().select().eq().eq().execute.return_value.data = []
        self.mock_supabase.table().select().eq().execute.return_value.data = []

        res = self.client.get(
            "/api/v1/shops/recommendations/personalized?latitude=14.55&longitude=121.01",
            headers=self.headers,
        )
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["status"], "insufficient_data")
        self.assertEqual(data["recommendations"], [])

    def test_endpoint_no_location_allowed(self):
        """Personalized recommendations are available without location."""
        shop_id = str(uuid4())
        user_reviews = [{"id": str(uuid4()), "shop_id": str(uuid4()), "rating": 5, "content": "Love pour-over coffee"}]
        candidate_reviews = [{"shop_id": shop_id, "content": "Specialty pour-over coffee", "rating": 5}]

        def table_fn(name):
            m = MagicMock()
            if name == "reviews":
                m.select().eq().eq().execute.return_value.data = user_reviews
                m.select().in_().eq().gte().execute.return_value.data = candidate_reviews
                m.select().in_().eq().execute.return_value.data = [{"shop_id": shop_id, "rating": 5}]
            elif name == "favorites":
                m.select().eq().execute.return_value.data = []
            elif name == "shops":
                m.select().order().limit().execute.return_value.data = [
                    {"id": shop_id, "name": "Global Café", "address": "Manila", "latitude": 14.5, "longitude": 121.0, "rating": 4.8, "google_place_id": "plc1"}
                ]
            elif name == "shop_curation":
                m.select().in_().eq().execute.return_value.data = [{"shop_id": shop_id, "status": "APPROVED"}]
            return m

        self.mock_supabase.table.side_effect = table_fn

        res = self.client.get("/api/v1/shops/recommendations/personalized", headers=self.headers)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        data = res.json()
        self.assertEqual(data["status"], "personalized")
        self.assertEqual(len(data["recommendations"]), 1)
        self.assertIsNone(data["recommendations"][0]["shop"]["distance_meters"])


if __name__ == "__main__":
    unittest.main()
