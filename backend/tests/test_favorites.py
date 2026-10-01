import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_authenticated_supabase, get_current_user
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.favorite import FavoriteStatusResponse
from app.services.favorites import FavoriteService


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="user1@example.com",
        user_metadata=None,
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = user_metadata or {"full_name": "User One"}


class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data if data is not None else []
        self.last_eq = None
        self.all_eq = []
        self.mock_execute = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = list(self._data) if self._data is not None else []
        self.mock_execute.return_value = mock_resp

    def select(self, cols="*"):
        return self

    def eq(self, col, val):
        self.last_eq = (col, val)
        self.all_eq.append((col, str(val)))
        if self.mock_execute.return_value.data is not None:
            self.mock_execute.return_value.data = [
                r for r in self.mock_execute.return_value.data
                if isinstance(r, dict) and (col not in r or str(r.get(col)) == str(val))
            ]
        return self

    def delete(self):
        mock_resp = MagicMock()
        mock_resp.data = []
        self.mock_execute.return_value = mock_resp
        return self

    def order(self, col, desc=False):
        if self.mock_execute.return_value.data is not None:
            reverse = bool(desc)
            try:
                self.mock_execute.return_value.data = sorted(
                    self.mock_execute.return_value.data,
                    key=lambda r: r.get(col, ""),
                    reverse=reverse,
                )
            except Exception:
                pass
        return self

    def in_(self, col, vals):
        str_vals = {str(v) for v in vals}
        if self.mock_execute.return_value.data is not None:
            self.mock_execute.return_value.data = [
                r for r in self.mock_execute.return_value.data
                if isinstance(r, dict) and str(r.get(col)) in str_vals
            ]
        return self

    def execute(self):
        return self.mock_execute()


class MockSupabaseClient:
    def __init__(self):
        self.tables = {}
        self.mock_rpc = MagicMock()

    def table(self, name):
        if name not in self.tables:
            self.tables[name] = MockQueryBuilder()
        return self.tables[name]

    def rpc(self, name, params=None):
        return self.mock_rpc(name, params)


class TestFavoritesEndpoints(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.shop_id = "123e4567-e89b-12d3-a456-426614174000"
        self.user1_id = "11111111-2222-3333-4444-555555555555"
        self.user2_id = "99999999-8888-7777-6666-555555555555"

        self.mock_user = UserResponse(
            id=self.user1_id,
            email="user1@example.com",
            created_at="2026-08-28T12:00:00Z",
            user_metadata={"full_name": "User One"},
            app_metadata={},
        )

        self.mock_supabase = MockSupabaseClient()
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase

    def tearDown(self):
        app.dependency_overrides.clear()

    def _setup_approved_shop(self):
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Craft Coffee", "rating": 4.5}
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": self.shop_id, "status": "APPROVED"}
        ])

    def test_get_favorite_status_when_favorited(self):
        """Returns is_favorite: true and timestamp when user has favorited the shop."""
        self._setup_approved_shop()
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {
                "id": "fav-1",
                "shop_id": self.shop_id,
                "user_id": self.user1_id,
                "created_at": "2026-09-30T01:00:00Z",
            }
        ])

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertTrue(data["is_favorite"])
        self.assertIsNotNone(data["favorited_at"])

    def test_get_favorite_status_when_not_favorited(self):
        """Returns is_favorite: false and null timestamp when user has not favorited the shop."""
        self._setup_approved_shop()
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([])

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertFalse(data["is_favorite"])
        self.assertIsNone(data["favorited_at"])

    def test_get_favorite_status_unauthenticated(self):
        """Returns 401 Unauthorized when no credentials are provided."""
        app.dependency_overrides.clear()
        response = self.client.get(f"/api/v1/shops/{self.shop_id}/favorite")
        self.assertEqual(response.status_code, 401)

    def test_get_favorite_status_shop_not_found(self):
        """Returns 404 Not Found when the shop does not exist."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([])
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Coffee shop not found.")

    def test_get_favorite_status_shop_not_approved(self):
        """Returns 404 Not Found when shop curation status is not APPROVED."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Excluded Shop"}
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": self.shop_id, "status": "EXCLUDED"}
        ])
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("not approved", response.json()["detail"])

    def test_get_favorite_status_curation_missing_row_defaults_to_pending(self):
        """When shop_curation row is missing, defaults fail-closed to PENDING_REVIEW (404)."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Shop Without Curation"}
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([])

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("not approved", response.json()["detail"])

    def test_get_favorite_status_curation_database_error_surfaces_as_500(self):
        """Database APIError while checking curation status raises HTTP 500."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Craft Coffee"}
        ])
        curation_builder = MockQueryBuilder()
        curation_builder.mock_execute.side_effect = APIError({"code": "XX000", "message": "DB connection dead"})
        self.mock_supabase.tables["shop_curation"] = curation_builder

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("A database error occurred while verifying coffee shop curation status.", response.json()["detail"])

    def test_get_favorite_status_curation_unexpected_error_surfaces_as_500(self):
        """Unexpected exception while checking curation status raises HTTP 500."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Craft Coffee"}
        ])
        curation_builder = MockQueryBuilder()
        curation_builder.mock_execute.side_effect = RuntimeError("Unexpected internal crash")
        self.mock_supabase.tables["shop_curation"] = curation_builder

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("An unexpected error occurred while processing the request.", response.json()["detail"])

    def test_create_favorite_curation_database_error_surfaces_as_500(self):
        """Database APIError while checking curation status during favorite creation raises HTTP 500."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Craft Coffee"}
        ])
        curation_builder = MockQueryBuilder()
        curation_builder.mock_execute.side_effect = APIError({"code": "XX000", "message": "DB connection dead"})
        self.mock_supabase.tables["shop_curation"] = curation_builder

        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("A database error occurred while verifying coffee shop curation status.", response.json()["detail"])

    def test_create_favorite_success(self):
        """Returns 201 Created with favorite details when favoriting an approved shop."""
        self._setup_approved_shop()
        rpc_builder = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = [{
            "id": "fav-123",
            "shop_id": self.shop_id,
            "user_id": self.user1_id,
            "created_at": "2026-09-30T02:00:00Z",
        }]
        rpc_builder.execute.return_value = mock_resp
        self.mock_supabase.mock_rpc.return_value = rpc_builder

        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertTrue(data["is_favorite"])
        self.assertIsNotNone(data["favorited_at"])
        self.mock_supabase.mock_rpc.assert_called_once_with(
            "create_user_favorite", {"p_shop_id": self.shop_id}
        )

    def test_create_favorite_duplicate_conflict(self):
        """Returns 409 Conflict when the user has already favorited the shop."""
        self._setup_approved_shop()
        rpc_builder = MagicMock()
        rpc_builder.execute.side_effect = APIError({"code": "23505", "message": "You have already favorited this coffee shop."})
        self.mock_supabase.mock_rpc.return_value = rpc_builder

        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already favorited", response.json()["detail"])

    def test_create_favorite_unauthenticated(self):
        """Returns 401 Unauthorized when unauthenticated."""
        app.dependency_overrides.clear()
        response = self.client.post(f"/api/v1/shops/{self.shop_id}/favorite")
        self.assertEqual(response.status_code, 401)

    def test_create_favorite_shop_not_found(self):
        """Returns 404 Not Found when creating a favorite for a nonexistent shop."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([])
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404)

    def test_create_favorite_shop_not_approved(self):
        """Returns 400 Bad Request when creating a favorite for an unapproved shop."""
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": self.shop_id, "name": "Pending Shop"}
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": self.shop_id, "status": "PENDING_REVIEW"}
        ])
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not approved", response.json()["detail"])

    def test_delete_favorite_success(self):
        """Returns 200 OK with success message when removing a favorite."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "fav-1", "shop_id": self.shop_id, "user_id": self.user1_id}
        ])

        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Coffee shop removed from favorites.")

    def test_delete_favorite_not_found(self):
        """Returns 404 Not Found when attempting to unfavorite a shop not favorited."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([])

        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 404)
        self.assertIn("not in your favorites", response.json()["detail"])

    def test_delete_favorite_unauthenticated(self):
        """Returns 401 Unauthorized when unauthenticated."""
        app.dependency_overrides.clear()
        response = self.client.delete(f"/api/v1/shops/{self.shop_id}/favorite")
        self.assertEqual(response.status_code, 401)

    def test_delete_favorite_allowed_even_if_shop_excluded(self):
        """Users can unfavorite a shop even if the shop is no longer APPROVED."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "fav-1", "shop_id": self.shop_id, "user_id": self.user1_id}
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": self.shop_id, "status": "EXCLUDED"}
        ])

        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer test-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Coffee shop removed from favorites.")

    # ------------------------------------------------------------------------
    # Explicit Cross-User Isolation Coverage at API & Database Security Boundary
    # ------------------------------------------------------------------------
    def test_cross_user_isolation_get_favorite_only_returns_callers_own(self):
        """User A querying /favorite cannot see User B's favorite for the same shop."""
        self._setup_approved_shop()
        # The database contains User B's favorite, but NOT User A's favorite
        user_b_favorite = {
            "id": "fav-user-b",
            "shop_id": self.shop_id,
            "user_id": self.user2_id,
            "created_at": "2026-09-30T01:30:00Z",
        }
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([user_b_favorite])

        # Current user is User A (user1_id)
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Must return false for User A, isolating User B's favorite
        self.assertFalse(data["is_favorite"])
        self.assertIsNone(data["favorited_at"])

        # Verify the database query explicitly filtered on caller's user_id
        fav_builder = self.mock_supabase.tables["favorites"]
        self.assertIn(("user_id", self.user1_id), fav_builder.all_eq)
        self.assertIn(("shop_id", self.shop_id), fav_builder.all_eq)

    def test_cross_user_isolation_delete_favorite_cannot_delete_other_user(self):
        """User A attempting to delete favorite cannot delete User B's favorite."""
        # The database contains User B's favorite
        user_b_favorite = {
            "id": "fav-user-b",
            "shop_id": self.shop_id,
            "user_id": self.user2_id,
            "created_at": "2026-09-30T01:30:00Z",
        }
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([user_b_favorite])

        # User A attempts to delete favorite for this shop
        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer user1-token"},
        )
        # Must return 404 because User A does not own a favorite for this shop
        self.assertEqual(response.status_code, 404)
        self.assertIn("not in your favorites", response.json()["detail"])

        # Verify query explicitly scoped to caller's user_id
        fav_builder = self.mock_supabase.tables["favorites"]
        self.assertIn(("user_id", self.user1_id), fav_builder.all_eq)

    def test_cross_user_isolation_create_favorite_derives_identity_from_auth(self):
        """Caller cannot supply or spoof another user's ID during favorite creation."""
        self._setup_approved_shop()
        rpc_builder = MagicMock()
        mock_resp = MagicMock()
        # Database RPC assigns auth.uid() automatically on the server
        mock_resp.data = [{
            "id": "fav-new",
            "shop_id": self.shop_id,
            "user_id": self.user1_id,
            "created_at": "2026-09-30T02:00:00Z",
        }]
        rpc_builder.execute.return_value = mock_resp
        self.mock_supabase.mock_rpc.return_value = rpc_builder

        # POST payload does not allow user_id injection; RPC strictly receives p_shop_id
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/favorite",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 201)
        # Ensure RPC was called strictly with shop_id, deriving user_id from Postgres auth context
        self.mock_supabase.mock_rpc.assert_called_once_with(
            "create_user_favorite", {"p_shop_id": self.shop_id}
        )
        self.assertNotIn("user_id", self.mock_supabase.mock_rpc.call_args[0][1])

    # =========================================================================
    # User Favorites List Tests (Issue #39)
    # =========================================================================

    def test_list_favorites_success(self):
        """Authenticated user retrieves their favorited approved coffee shops ordered by most recent."""
        shop1_id = "11111111-1111-1111-1111-111111111111"
        shop2_id = "22222222-2222-2222-2222-222222222222"

        # User has two favorites, shop2 favorited more recently than shop1
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {
                "id": "fav-1",
                "shop_id": shop1_id,
                "user_id": self.user1_id,
                "created_at": "2026-09-30T10:00:00Z",
            },
            {
                "id": "fav-2",
                "shop_id": shop2_id,
                "user_id": self.user1_id,
                "created_at": "2026-10-01T12:00:00Z",
            },
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": shop1_id, "status": "APPROVED"},
            {"shop_id": shop2_id, "status": "APPROVED"},
        ])
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {
                "id": shop1_id,
                "name": "First Coffee",
                "address": "123 First St",
                "latitude": 14.5995,
                "longitude": 120.9842,
                "rating": 4.5,
                "google_place_id": "place-1",
                "created_at": "2026-08-01T00:00:00Z",
                "updated_at": "2026-08-01T00:00:00Z",
            },
            {
                "id": shop2_id,
                "name": "Second Coffee",
                "address": "456 Second St",
                "latitude": 14.6000,
                "longitude": 120.9850,
                "rating": 4.8,
                "google_place_id": "place-2",
                "created_at": "2026-08-02T00:00:00Z",
                "updated_at": "2026-08-02T00:00:00Z",
            },
        ])

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 2)
        # Most recently favorited first (shop2 then shop1)
        self.assertEqual(data[0]["id"], shop2_id)
        self.assertEqual(data[0]["name"], "Second Coffee")
        self.assertEqual(data[0]["rating"], 4.8)
        self.assertEqual(data[0]["favorited_at"], "2026-10-01T12:00:00Z")

        self.assertEqual(data[1]["id"], shop1_id)
        self.assertEqual(data[1]["name"], "First Coffee")
        self.assertEqual(data[1]["rating"], 4.5)
        self.assertEqual(data[1]["favorited_at"], "2026-09-30T10:00:00Z")

    def test_list_favorites_empty(self):
        """Authenticated user with no favorites receives an empty list."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([])
        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_favorites_unauthorized(self):
        """Unauthenticated request to list favorites returns 401 Unauthorized."""
        app.dependency_overrides.clear()
        response = self.client.get("/api/v1/favorites")
        self.assertEqual(response.status_code, 401)

    def test_list_favorites_user_ownership_isolation(self):
        """Favorites query strictly isolates caller favorites from other users."""
        shop1_id = "11111111-1111-1111-1111-111111111111"
        shop2_id = "22222222-2222-2222-2222-222222222222"

        # User 1 has shop1, User 2 has shop2
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {
                "id": "fav-user1",
                "shop_id": shop1_id,
                "user_id": self.user1_id,
                "created_at": "2026-09-30T10:00:00Z",
            },
            {
                "id": "fav-user2",
                "shop_id": shop2_id,
                "user_id": self.user2_id,
                "created_at": "2026-09-30T11:00:00Z",
            },
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": shop1_id, "status": "APPROVED"},
            {"shop_id": shop2_id, "status": "APPROVED"},
        ])
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {
                "id": shop1_id,
                "name": "User 1 Coffee",
                "latitude": 14.5995,
                "longitude": 120.9842,
            },
            {
                "id": shop2_id,
                "name": "User 2 Coffee",
                "latitude": 14.6000,
                "longitude": 120.9850,
            },
        ])

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], shop1_id)
        self.assertEqual(data[0]["name"], "User 1 Coffee")

        # Verify query explicitly scoped to caller's user_id
        fav_builder = self.mock_supabase.tables["favorites"]
        self.assertIn(("user_id", self.user1_id), fav_builder.all_eq)

    def test_list_favorites_excludes_non_approved_shops(self):
        """Only currently APPROVED shops are returned in the Favorites list."""
        shop_app_id = "11111111-1111-1111-1111-111111111111"
        shop_pen_id = "22222222-2222-2222-2222-222222222222"
        shop_exc_id = "33333333-3333-3333-3333-333333333333"

        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "f1", "shop_id": shop_app_id, "user_id": self.user1_id, "created_at": "2026-10-01T01:00:00Z"},
            {"id": "f2", "shop_id": shop_pen_id, "user_id": self.user1_id, "created_at": "2026-10-01T02:00:00Z"},
            {"id": "f3", "shop_id": shop_exc_id, "user_id": self.user1_id, "created_at": "2026-10-01T03:00:00Z"},
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": shop_app_id, "status": "APPROVED"},
            {"shop_id": shop_pen_id, "status": "PENDING_REVIEW"},
            {"shop_id": shop_exc_id, "status": "EXCLUDED"},
        ])
        self.mock_supabase.tables["shops"] = MockQueryBuilder([
            {"id": shop_app_id, "name": "Approved Shop", "latitude": 14.5995, "longitude": 120.9842},
            {"id": shop_pen_id, "name": "Pending Shop", "latitude": 14.6000, "longitude": 120.9850},
            {"id": shop_exc_id, "name": "Excluded Shop", "latitude": 14.6005, "longitude": 120.9860},
        ])

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], shop_app_id)
        self.assertEqual(data[0]["name"], "Approved Shop")

    def test_list_favorites_missing_shop_handled_gracefully(self):
        """If a favorited shop row has no corresponding record in shops, it is omitted cleanly."""
        missing_shop_id = "44444444-4444-4444-4444-444444444444"
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "f1", "shop_id": missing_shop_id, "user_id": self.user1_id, "created_at": "2026-10-01T01:00:00Z"},
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": missing_shop_id, "status": "APPROVED"},
        ])
        self.mock_supabase.tables["shops"] = MockQueryBuilder([])

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), [])

    def test_list_favorites_database_error_on_favorites(self):
        """Database error querying favorites table returns sanitized 500."""
        fav_builder = MockQueryBuilder()
        fav_builder.mock_execute.side_effect = APIError({"message": "DB connection dead", "code": "08006"})
        self.mock_supabase.tables["favorites"] = fav_builder

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("database error occurred while retrieving favorites", response.json()["detail"])

    def test_list_favorites_database_error_on_curation(self):
        """Database error querying shop_curation returns sanitized 500."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "f1", "shop_id": self.shop_id, "user_id": self.user1_id, "created_at": "2026-10-01T01:00:00Z"},
        ])
        cur_builder = MockQueryBuilder()
        cur_builder.mock_execute.side_effect = APIError({"message": "Curation read failed", "code": "50000"})
        self.mock_supabase.tables["shop_curation"] = cur_builder

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("database error occurred while verifying coffee shop curation status", response.json()["detail"])

    def test_list_favorites_database_error_on_shops(self):
        """Database error querying shops table returns sanitized 500."""
        self.mock_supabase.tables["favorites"] = MockQueryBuilder([
            {"id": "f1", "shop_id": self.shop_id, "user_id": self.user1_id, "created_at": "2026-10-01T01:00:00Z"},
        ])
        self.mock_supabase.tables["shop_curation"] = MockQueryBuilder([
            {"shop_id": self.shop_id, "status": "APPROVED"},
        ])
        shops_builder = MockQueryBuilder()
        shops_builder.mock_execute.side_effect = APIError({"message": "Shops read failed", "code": "50000"})
        self.mock_supabase.tables["shops"] = shops_builder

        response = self.client.get(
            "/api/v1/favorites",
            headers={"Authorization": "Bearer user1-token"},
        )
        self.assertEqual(response.status_code, 500)
        self.assertIn("database error occurred while retrieving favorite shops", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()

