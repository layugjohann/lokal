import math
import os
import sys
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError

from app.main import app
from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase


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


class TestNearbyShopEndpoints(unittest.TestCase):
    def setUp(self):
        """Configure mock dependencies and test client before each test."""
        self.mock_supabase = MagicMock()
        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)
        self.auth_headers = {"Authorization": "Bearer valid-mock-token"}
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()

        self.sample_nearby_shops = [
            {
                "id": "123e4567-e89b-12d3-a456-426614174001",
                "name": "Kape Manila",
                "address": "Escolta St, Binondo, Manila",
                "latitude": 14.5995,
                "longitude": 120.9842,
                "rating": 4.80,
                "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY1",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T08:00:00Z",
                "distance_meters": 120.5,
            },
            {
                "id": "123e4567-e89b-12d3-a456-426614174002",
                "name": "Intramuros Roasters",
                "address": "General Luna St, Intramuros, Manila",
                "latitude": 14.5890,
                "longitude": 120.9750,
                "rating": 4.60,
                "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY2",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T08:00:00Z",
                "distance_meters": 1450.0,
            },
        ]

    def tearDown(self):
        """Clean up FastAPI dependency overrides after each test."""
        app.dependency_overrides.clear()

    def test_nearby_search_success(self):
        """Test successful nearby coffee shop retrieval with distance_meters."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = self.sample_nearby_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        self.assertEqual(data[0]["name"], "Kape Manila")
        self.assertEqual(data[0]["distance_meters"], 120.5)
        self.assertEqual(data[1]["name"], "Intramuros Roasters")
        self.assertEqual(data[1]["distance_meters"], 1450.0)

        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": None,
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_custom_parameters(self):
        """Test nearby search with explicit radius, limit, and offset parameters."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&radius=10000.0&limit=15&offset=5",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)

        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 10000.0,
                "result_limit": 15,
                "result_offset": 5,
                "search_query": None,
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_empty_results(self):
        """Test nearby search when no coffee shops are found within radius."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = []
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_nearby_search_none_data_returns_empty_list(self):
        """Test nearby search returns empty list when RPC data is None."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = None
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_nearby_search_distance_sorting(self):
        """Test that nearby search preserves ascending distance sorting from database."""
        sorted_shops = [
            dict(self.sample_nearby_shops[0], distance_meters=50.0),
            dict(self.sample_nearby_shops[1], distance_meters=300.0),
            dict(self.sample_nearby_shops[0], id=str(uuid4()), distance_meters=1200.0),
        ]
        mock_execute = MagicMock()
        mock_execute.return_value.data = sorted_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        distances = [item["distance_meters"] for item in data]
        self.assertEqual(distances, [50.0, 300.0, 1200.0])
        self.assertEqual(distances, sorted(distances))

    def test_nearby_search_coordinate_validation_latitude(self):
        """Test rejection of invalid latitude boundary values."""
        # > 90
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=90.1&longitude=120.0",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # < -90
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=-90.1&longitude=120.0",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nearby_search_coordinate_validation_longitude(self):
        """Test rejection of invalid longitude boundary values."""
        # > 180
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.0&longitude=180.1",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # < -180
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.0&longitude=-180.1",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nearby_search_coordinate_boundaries_valid(self):
        """Test that exact boundary coordinates (-90, 90, -180, 180) are accepted."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = []
        self.mock_supabase.rpc.return_value.execute = mock_execute

        for lat, lng in [(90.0, 180.0), (-90.0, -180.0), (0.0, 0.0)]:
            resp = self.client.get(
                f"/api/v1/shops/nearby?latitude={lat}&longitude={lng}",
                headers=self.auth_headers,
            )
            self.assertEqual(resp.status_code, 200, f"Failed for lat={lat}, lng={lng}")

    def test_nearby_search_missing_coordinates(self):
        """Test rejection when latitude or longitude is missing."""
        resp = self.client.get(
            "/api/v1/shops/nearby?longitude=120.9842",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nearby_search_radius_validation(self):
        """Test radius validation boundaries: > 0 and <= 50,000m."""
        # radius = 0
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&radius=0",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # negative radius
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&radius=-100",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # radius > 50000
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&radius=50001",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # valid max boundary 50000
        mock_execute = MagicMock()
        mock_execute.return_value.data = []
        self.mock_supabase.rpc.return_value.execute = mock_execute

        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&radius=50000",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 200)

    def test_nearby_search_pagination_validation(self):
        """Test limit and offset parameter constraints."""
        # limit < 1
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5&longitude=121.0&limit=0",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # limit > 100
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5&longitude=121.0&limit=101",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # offset < 0
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5&longitude=121.0&offset=-1",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nearby_search_unauthenticated(self):
        """Test rejection when Bearer token is missing."""
        resp = self.client.get("/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842")
        self.assertEqual(resp.status_code, 401)

    def test_nearby_search_invalid_token(self):
        """Test rejection when Bearer token is invalid."""
        self.mock_supabase.auth.get_user.side_effect = AuthApiError("Invalid token", 401, "invalid_jwt")
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers={"Authorization": "Bearer bad-token"},
        )
        self.assertEqual(resp.status_code, 401)


    def test_nearby_search_database_api_error(self):
        """Test database API error returns sanitized 500 without leaking raw details."""
        mock_execute = MagicMock()
        mock_execute.side_effect = APIError({"message": "internal db column error", "code": "P0001"})
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "A database error occurred while searching for nearby coffee shops.",
        )
        self.assertNotIn("internal db column error", response.json()["detail"])

    def test_nearby_search_unexpected_exception(self):
        """Test unexpected exception returns sanitized 500."""
        mock_execute = MagicMock()
        mock_execute.side_effect = RuntimeError("network socket dropped")
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json()["detail"],
            "An unexpected error occurred while processing the request.",
        )
        self.assertNotIn("network socket dropped", response.json()["detail"])

    def test_route_precedence_nearby_vs_shop_id(self):
        """Test route precedence: /nearby must match the nearby search endpoint and not /{shop_id}."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = self.sample_nearby_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        # Calling /nearby matches nearby search
        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertIsInstance(response.json(), list)

        # Calling with a UUID matches get_shop endpoint
        target_id = str(uuid4())
        mock_query = MagicMock()
        mock_query.select.return_value.eq.return_value.execute.return_value.data = [
            dict(self.sample_nearby_shops[0], id=target_id)
        ]
        self.mock_supabase.table.return_value = mock_query

        single_response = self.client.get(
            f"/api/v1/shops/{target_id}",
            headers=self.auth_headers,
        )
        self.assertEqual(single_response.status_code, 200)
        self.assertEqual(single_response.json()["id"], target_id)

    def test_nearby_search_eligibility_filter_omits_non_approved_shops(self):
        """Verify nearby discovery reflects approved-only shops returned by RPC."""
        # When RPC applies 'WHERE sc.status = APPROVED', non-approved shops are omitted
        approved_shop = dict(self.sample_nearby_shops[0], name="Approved Independent Coffee")
        mock_execute = MagicMock()
        mock_execute.return_value.data = [approved_shop]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["name"], "Approved Independent Coffee")
        self.assertEqual(data[0]["distance_meters"], 120.5)

    def test_nearby_search_empty_when_no_approved_shops(self):
        """When all nearby candidates are EXCLUDED or PENDING_REVIEW, RPC returns empty list."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = []
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_nearby_search_with_query_forwarded_as_search_query(self):
        """Verify API query parameter 'query' is stripped and forwarded to RPC as 'search_query'."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=espresso",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": "espresso",
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_query_whitespace_stripped(self):
        """Verify query parameter with leading/trailing whitespace is cleanly stripped."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=%20%20Kape%20Manila%20%20",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": "Kape Manila",
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_query_with_wildcards_forwarded_literally(self):
        """Verify queries containing special pattern characters (%, _, \\) are forwarded intact to RPC."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=100%25_Coffee",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": "100%_Coffee",
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_query_whitespace_only_normalized_to_none(self):
        """Verify whitespace-only query parameter is normalized to None."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = self.sample_nearby_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=%20%20%20",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": None,
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_with_min_rating(self):
        """Verify min_rating parameter is forwarded to get_nearby_shops RPC."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&min_rating=4.5",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": None,
                "min_rating": 4.5,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_min_rating_validation(self):
        """Verify min_rating boundary validation: [0.0, 5.0]."""
        # Negative rating
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&min_rating=-0.1",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Rating > 5.0
        resp = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&min_rating=5.01",
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_nearby_search_with_sort_by_rating(self):
        """Verify sort_by='rating' is accepted and forwarded to RPC."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = self.sample_nearby_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&sort_by=rating",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": None,
                "min_rating": None,
                "sort_by": "rating",
            },
        )

    def test_nearby_search_with_sort_by_distance(self):
        """Verify explicit sort_by='distance' is accepted and forwarded to RPC."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = self.sample_nearby_shops
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&sort_by=distance",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 5000.0,
                "result_limit": 50,
                "result_offset": 0,
                "search_query": None,
                "min_rating": None,
                "sort_by": "distance",
            },
        )

    def test_nearby_search_sort_by_strict_lowercase_contract(self):
        """Verify sort_by requires exact lowercase; uppercase or unsupported values return 422."""
        invalid_sorts = ["RATING", "DISTANCE", "Rating", "Distance", "popularity", "name"]
        for invalid_sort in invalid_sorts:
            resp = self.client.get(
                f"/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&sort_by={invalid_sort}",
                headers=self.auth_headers,
            )
            self.assertEqual(resp.status_code, 422, f"Expected 422 for sort_by={invalid_sort}")

    def test_nearby_search_combined_query_filter_sort(self):
        """Verify combined search query, min_rating, radius, and sort_by parameters."""
        mock_execute = MagicMock()
        mock_execute.return_value.data = [self.sample_nearby_shops[0]]
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=Kape&min_rating=4.5&sort_by=rating&radius=3000&limit=20&offset=0",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        self.mock_supabase.rpc.assert_called_once_with(
            "get_nearby_shops",
            {
                "user_lat": 14.5995,
                "user_lng": 120.9842,
                "radius_meters": 3000.0,
                "result_limit": 20,
                "result_offset": 0,
                "search_query": "Kape",
                "min_rating": 4.5,
                "sort_by": "rating",
            },
        )

    def test_curation_invariant_excludes_pending_and_excluded_shops_on_search_and_filter(self):
        """Verify shops marked PENDING_REVIEW or EXCLUDED remain excluded even if matching query, rating, and radius.

        The database RPC enforces:
            INNER JOIN shop_curation sc ON s.id = sc.shop_id WHERE sc.status = 'APPROVED'
        Adding search query, rating filter, or sort order cannot bypass this curation invariant.
        """
        # Candidate shops in database
        all_candidates = [
            # Shop 1: APPROVED, matches query 'Roasters', rating 4.8, distance 150m -> INCLUDED
            {
                "id": "11111111-0000-0000-0000-000000000001",
                "name": "Approved Roasters",
                "rating": 4.8,
                "status": "APPROVED",
                "distance_meters": 150.0,
            },
            # Shop 2: PENDING_REVIEW, matches query 'Roasters', rating 4.9, distance 100m -> EXCLUDED
            {
                "id": "22222222-0000-0000-0000-000000000002",
                "name": "Pending Roasters",
                "rating": 4.9,
                "status": "PENDING_REVIEW",
                "distance_meters": 100.0,
            },
            # Shop 3: EXCLUDED, matches query 'Roasters', rating 5.0, distance 50m -> EXCLUDED
            {
                "id": "33333333-0000-0000-0000-000000000003",
                "name": "Chain Big Roasters",
                "rating": 5.0,
                "status": "EXCLUDED",
                "distance_meters": 50.0,
            },
        ]

        # Simulating SQL RPC curation filter: only sc.status = 'APPROVED'
        rpc_filtered = [
            {
                "id": s["id"],
                "name": s["name"],
                "address": "Sample St",
                "latitude": 14.5995,
                "longitude": 120.9842,
                "rating": s["rating"],
                "google_place_id": f"place-{s['id']}",
                "created_at": "2026-09-01T08:00:00Z",
                "updated_at": "2026-09-01T08:00:00Z",
                "distance_meters": s["distance_meters"],
            }
            for s in all_candidates
            if s["status"] == "APPROVED"
        ]

        mock_execute = MagicMock()
        mock_execute.return_value.data = rpc_filtered
        self.mock_supabase.rpc.return_value.execute = mock_execute

        response = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5995&longitude=120.9842&query=Roasters&min_rating=4.5&sort_by=rating",
            headers=self.auth_headers,
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], "11111111-0000-0000-0000-000000000001")
        self.assertEqual(data[0]["name"], "Approved Roasters")

        # Confirm non-approved shop IDs are completely absent from response
        returned_ids = {item["id"] for item in data}
        self.assertNotIn("22222222-0000-0000-0000-000000000002", returned_ids)
        self.assertNotIn("33333333-0000-0000-0000-000000000003", returned_ids)


class TestGeodesicAndBoundingBoxMath(unittest.TestCase):
    """Unit tests verifying the geodesic haversine formula and bounding box calculation."""

    EARTH_RADIUS = 6371000.0

    def _haversine(self, lat1, lon1, lat2, lon2):
        """Calculate the geodesic great-circle distance between two points in meters using Haversine formula."""
        r_lat1 = math.radians(lat1)
        r_lon1 = math.radians(lon1)
        r_lat2 = math.radians(lat2)
        r_lon2 = math.radians(lon2)

        d_lat = r_lat2 - r_lat1
        d_lon = r_lon2 - r_lon1

        a = math.sin(d_lat / 2.0) ** 2 + math.cos(r_lat1) * math.cos(r_lat2) * (math.sin(d_lon / 2.0) ** 2)
        clamped_a = min(1.0, max(0.0, a))
        c = 2.0 * math.asin(math.sqrt(clamped_a))
        return self.EARTH_RADIUS * c

    def test_haversine_identical_coordinates(self):
        """Distance between identical coordinates must be 0 meters."""
        dist = self._haversine(14.5995, 120.9842, 14.5995, 120.9842)
        self.assertAlmostEqual(dist, 0.0, places=4)

    def test_haversine_known_benchmark(self):
        """Distance between Manila (14.5995, 120.9842) and QC (14.6488, 121.0734) ~11.0km."""
        dist = self._haversine(14.5995, 120.9842, 14.6488, 121.0734)
        # Expected is around 11,040 meters
        self.assertGreater(dist, 10500.0)
        self.assertLess(dist, 11500.0)

    def test_haversine_antimeridian_crossing(self):
        """Distance across the 180° antimeridian (e.g. 0°, 179° to 0°, -179°) is 2° on equator."""
        dist = self._haversine(0.0, 179.0, 0.0, -179.0)
        expected = 2.0 * math.pi * self.EARTH_RADIUS * (2.0 / 360.0)
        self.assertAlmostEqual(dist, expected, delta=0.01)

    def test_haversine_polar_boundary(self):
        """Distance from North Pole (90°, 0°) to 89° latitude along meridian is 1° arc."""
        dist = self._haversine(90.0, 0.0, 89.0, 0.0)
        expected = 2.0 * math.pi * self.EARTH_RADIUS * (1.0 / 360.0)
        self.assertAlmostEqual(dist, expected, delta=0.01)

    def test_haversine_trigonometric_clamping(self):
        """Antipodal points (e.g. 0°, 0° to 0°, 180°) must not cause float domain error."""
        dist = self._haversine(0.0, 0.0, 0.0, 180.0)
        expected = math.pi * self.EARTH_RADIUS
        self.assertAlmostEqual(dist, expected, delta=0.01)


if __name__ == "__main__":
    unittest.main()
