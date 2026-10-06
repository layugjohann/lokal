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
from app.schemas.community import CommunityFeedItem, CommunityFeedResponse
from app.services.community import CommunityService


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="testuser@example.com",
        user_metadata=None,
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = user_metadata or {"full_name": "Test User"}


class TestCommunityFeed(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.mock_user = DummyUser()
        self.mock_supabase = MagicMock()

        # Override dependencies by default
        app.dependency_overrides[get_current_user] = lambda: self.mock_user
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_feed_requires_authentication(self):
        """Unauthenticated request must be rejected with 401 Unauthorized."""
        app.dependency_overrides.clear()
        response = self.client.get("/api/v1/community/feed")
        self.assertEqual(response.status_code, 401)

    def test_feed_success_with_items_and_has_more_true(self):
        """When RPC returns (limit + 1) rows, endpoint returns limit items and has_more=True."""
        limit = 3
        now_iso = datetime.now(timezone.utc).isoformat()
        # Return 4 rows for limit = 3
        mock_rows = [
            {
                "id": str(uuid4()),
                "shop_id": str(uuid4()),
                "shop_name": f"Cafe {i}",
                "shop_address": f"{i} Main St",
                "author_name": f"User {i}",
                "rating": 5 - (i % 3),
                "content": f"Review content {i}",
                "created_at": now_iso,
                "updated_at": now_iso,
            }
            for i in range(1, 5)
        ]

        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = mock_rows
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get(f"/api/v1/community/feed?limit={limit}&offset=0")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["limit"], limit)
        self.assertEqual(data["offset"], 0)
        self.assertTrue(data["has_more"])
        self.assertEqual(len(data["items"]), limit)
        self.assertEqual(data["items"][0]["shop_name"], "Cafe 1")
        self.assertEqual(data["items"][2]["shop_name"], "Cafe 3")

        # Verify RPC was called with clamped params
        self.mock_supabase.rpc.assert_called_once_with(
            "get_community_feed",
            {"p_limit": limit, "p_offset": 0},
        )

    def test_feed_success_with_has_more_false(self):
        """When RPC returns <= limit rows, endpoint returns all items and has_more=False."""
        limit = 5
        now_iso = datetime.now(timezone.utc).isoformat()
        mock_rows = [
            {
                "id": str(uuid4()),
                "shop_id": str(uuid4()),
                "shop_name": "Single Cafe",
                "shop_address": "123 Coffee Way",
                "author_name": "Solo Brewer",
                "rating": 5,
                "content": "Only review here.",
                "created_at": now_iso,
                "updated_at": now_iso,
            }
        ]

        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = mock_rows
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get(f"/api/v1/community/feed?limit={limit}&offset=0")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertFalse(data["has_more"])
        self.assertEqual(len(data["items"]), 1)
        self.assertEqual(data["items"][0]["author_name"], "Solo Brewer")

    def test_feed_empty_response(self):
        """When RPC returns 0 rows, endpoint returns empty items and has_more=False."""
        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = []
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get("/api/v1/community/feed")
        self.assertEqual(response.status_code, 200)

        data = response.json()
        self.assertEqual(data["items"], [])
        self.assertFalse(data["has_more"])
        self.assertEqual(data["limit"], 20)
        self.assertEqual(data["offset"], 0)

    def test_feed_privacy_and_identifier_contract(self):
        """Application IDs (id, shop_id) are present; private user_id, email, curator data are absent."""
        review_id = str(uuid4())
        shop_id = str(uuid4())
        c_time = "2026-10-01T10:00:00Z"
        u_time = "2026-10-02T12:00:00Z"

        mock_row = {
            "id": review_id,
            "shop_id": shop_id,
            "shop_name": "Privacy Cafe",
            "shop_address": "Secure St",
            "author_name": "Snapshot Name",
            "rating": 4,
            "content": "Nice brew",
            "created_at": c_time,
            "updated_at": u_time,
            # Hypothetical private columns that must never be exposed
            "user_id": "secret-user-uuid",
            "email": "secret@example.com",
            "curator_notes": "internal note",
        }

        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [mock_row]
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get("/api/v1/community/feed?limit=10&offset=0")
        self.assertEqual(response.status_code, 200)

        item = response.json()["items"][0]
        # Application identifiers permitted for client coordination
        self.assertEqual(item["id"], review_id)
        self.assertEqual(item["shop_id"], shop_id)
        self.assertEqual(item["shop_name"], "Privacy Cafe")
        self.assertEqual(item["author_name"], "Snapshot Name")
        # is_edited should be true since updated_at > created_at
        self.assertTrue(item["is_edited"])

        # Private fields must not be present in response item
        self.assertNotIn("user_id", item)
        self.assertNotIn("email", item)
        self.assertNotIn("curator_notes", item)

    def test_feed_is_edited_false_when_unmodified(self):
        """When updated_at equals created_at, is_edited is False."""
        same_time = "2026-10-01T10:00:00Z"
        mock_row = {
            "id": str(uuid4()),
            "shop_id": str(uuid4()),
            "shop_name": "Cafe Same Time",
            "shop_address": None,
            "author_name": "Author",
            "rating": 5,
            "content": "Great",
            "created_at": same_time,
            "updated_at": same_time,
        }

        mock_rpc = MagicMock()
        mock_rpc.execute.return_value.data = [mock_row]
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get("/api/v1/community/feed")
        self.assertEqual(response.status_code, 200)
        item = response.json()["items"][0]
        self.assertFalse(item["is_edited"])

    def test_feed_query_param_validation(self):
        """FastAPI enforces bounds on limit (1-50) and offset (>= 0)."""
        # limit > 50 rejected
        res_limit_high = self.client.get("/api/v1/community/feed?limit=51")
        self.assertEqual(res_limit_high.status_code, 422)

        # limit < 1 rejected
        res_limit_low = self.client.get("/api/v1/community/feed?limit=0")
        self.assertEqual(res_limit_low.status_code, 422)

        # offset < 0 rejected
        res_offset_neg = self.client.get("/api/v1/community/feed?offset=-1")
        self.assertEqual(res_offset_neg.status_code, 422)

    def test_feed_database_error_handling(self):
        """Database APIError must be caught and returned as sanitized 500 error."""
        mock_rpc = MagicMock()
        mock_rpc.execute.side_effect = APIError({"message": "DB connection dead", "code": "50000"})
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get("/api/v1/community/feed")
        self.assertEqual(response.status_code, 500)
        self.assertIn("A database error occurred", response.json()["detail"])

    def test_feed_unexpected_error_handling(self):
        """Unexpected exception must be caught and returned as sanitized 500 error."""
        mock_rpc = MagicMock()
        mock_rpc.execute.side_effect = RuntimeError("Something unexpected")
        self.mock_supabase.rpc.return_value = mock_rpc

        response = self.client.get("/api/v1/community/feed")
        self.assertEqual(response.status_code, 500)
        self.assertIn("An unexpected error occurred", response.json()["detail"])


if __name__ == "__main__":
    unittest.main()
