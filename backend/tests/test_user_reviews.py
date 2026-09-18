import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.review import (
    ProviderAttribution,
    ReviewAuthor,
    ReviewCreate,
    ReviewSource,
    ReviewUpdate,
    ShopReviewsResponse,
    UnifiedReview,
)
from app.services.reviews.service import ReviewService


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
        self.user_metadata = user_metadata if user_metadata is not None else {"full_name": "Maria Santos"}


class DummyUserResponse:
    def __init__(self, user=Ellipsis):
        if user is Ellipsis:
            self.user = DummyUser()
        else:
            self.user = user


class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data if data is not None else []
        self.last_eq = None
        self.last_order = None
        self.last_inserted = None
        self.last_updated = None
        self.mock_execute = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = self._data
        self.mock_execute.return_value = mock_resp

    def select(self, cols="*"):
        return self

    def eq(self, col, val):
        self.last_eq = (col, val)
        return self

    def order(self, col, desc=False):
        self.last_order = (col, desc)
        return self

    def insert(self, payload):
        self.last_inserted = payload
        mock_resp = MagicMock()
        if isinstance(payload, dict):
            created_row = dict(payload)
            if "id" not in created_row:
                created_row["id"] = "22222222-3333-4444-5555-666666666666"
            if "created_at" not in created_row:
                created_row["created_at"] = "2026-09-19T02:00:00Z"
            if "updated_at" not in created_row:
                created_row["updated_at"] = "2026-09-19T02:00:00Z"
            mock_resp.data = [created_row]
        else:
            mock_resp.data = []
        self.mock_execute.return_value = mock_resp
        return self

    def update(self, payload):
        self.last_updated = payload
        mock_resp = MagicMock()
        updated_row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": "123e4567-e89b-12d3-a456-426614174000",
            "user_id": "11111111-2222-3333-4444-555555555555",
            "author_name": "Maria Santos",
            "rating": 4,
            "content": "Updated content",
            "source": "lokal",
            "created_at": "2026-09-19T02:00:00Z",
            "updated_at": "2026-09-19T02:30:00Z",
        }
        updated_row.update(payload)
        mock_resp.data = [updated_row]
        self.mock_execute.return_value = mock_resp
        return self

    def delete(self):
        mock_resp = MagicMock()
        mock_resp.data = [{"id": "deleted"}]
        self.mock_execute.return_value = mock_resp
        return self

    def execute(self):
        return self.mock_execute()


class TestUserReviewEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()
        self.shop_id = "123e4567-e89b-12d3-a456-426614174000"
        self.user_id = "11111111-2222-3333-4444-555555555555"

        self.shops_builder = MockQueryBuilder(data=[{
            "id": self.shop_id,
            "name": "Artisan Café",
            "rating": 4.5,
            "google_place_id": None,
        }])
        self.curation_builder = MockQueryBuilder(data=[{"status": "APPROVED"}])
        self.reviews_builder = MockQueryBuilder(data=[])

        def table_router(table_name):
            if table_name == "shops":
                return self.shops_builder
            elif table_name == "shop_curation":
                return self.curation_builder
            elif table_name == "reviews":
                return self.reviews_builder
            return MockQueryBuilder(data=[])

        self.mock_supabase.table.side_effect = table_router
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()

        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)
        self.auth_headers = {"Authorization": "Bearer mock-test-token"}

    def tearDown(self):
        app.dependency_overrides.clear()

    # --- 1. POST /api/v1/shops/{shop_id}/reviews Tests ---

    def test_create_review_success_with_text(self):
        payload = {
            "rating": 5,
            "content": "Outstanding flat white and great service!",
        }
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["text"], "Outstanding flat white and great service!")
        self.assertEqual(data["source"], "lokal")
        self.assertEqual(data["author"]["display_name"], "Maria Santos")
        self.assertFalse(data["is_edited"])
        self.assertIsNone(data["updated_at"])
        # Privacy check: email and user UUID are not leaked in author payload
        self.assertNotIn("testuser@example.com", str(data))
        self.assertNotIn(self.user_id, str(data["author"]))

    def test_create_review_success_rating_only_empty_content(self):
        payload = {"rating": 4}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["rating"], 4)
        self.assertIsNone(data["text"])

    def test_create_review_whitespace_content_normalized_to_none(self):
        payload = {"rating": 4, "content": "    "}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertIsNone(data["text"])
        self.assertIsNone(self.reviews_builder.last_inserted["content"])

    def test_create_review_fallback_author_name_when_no_metadata(self):
        dummy_user = DummyUser(user_metadata={})
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse(user=dummy_user)

        payload = {"rating": 5}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 201)
        data = response.json()
        self.assertEqual(data["author"]["display_name"], "LOKAL User")

    def test_create_review_invalid_rating_below_one(self):
        payload = {"rating": 0}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_create_review_invalid_rating_above_five(self):
        payload = {"rating": 6}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_create_review_invalid_content_too_long(self):
        payload = {"rating": 5, "content": "a" * 1001}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_create_review_shop_not_found(self):
        self.shops_builder = MockQueryBuilder(data=[])
        payload = {"rating": 5}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Coffee shop not found.")

    def test_create_review_blocked_when_shop_excluded(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "EXCLUDED"}])
        payload = {"rating": 5}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not approved for public discovery", response.json()["detail"])

    def test_create_review_blocked_when_shop_pending_review(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "PENDING_REVIEW"}])
        payload = {"rating": 5}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not approved for public discovery", response.json()["detail"])

    def test_create_review_duplicate_conflict_409(self):
        self.reviews_builder.insert = MagicMock()
        mock_exec = MagicMock()
        mock_exec.execute.side_effect = APIError({
            "message": "duplicate key value violates unique constraint",
            "code": "23505",
        })
        self.reviews_builder.insert.return_value = mock_exec

        payload = {"rating": 5}
        response = self.client.post(
            f"/api/v1/shops/{self.shop_id}/reviews",
            json=payload,
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 409)
        self.assertIn("already reviewed", response.json()["detail"])

    # --- 2. GET /api/v1/shops/{shop_id}/reviews/mine Tests ---

    def test_get_my_review_success(self):
        row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 5,
            "content": "Loved the espresso!",
            "source": "lokal",
            "created_at": "2026-09-19T02:00:00Z",
            "updated_at": "2026-09-19T02:00:00Z",
        }
        self.reviews_builder = MockQueryBuilder(data=[row])

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rating"], 5)
        self.assertEqual(data["text"], "Loved the espresso!")
        self.assertEqual(data["author"]["display_name"], "Maria Santos")
        self.assertFalse(data["is_edited"])

    def test_get_my_review_not_found(self):
        self.reviews_builder = MockQueryBuilder(data=[])
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "You have not reviewed this coffee shop.")

    def test_get_my_review_allowed_when_shop_excluded(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "EXCLUDED"}])
        row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 4,
            "content": "Good spot.",
            "source": "lokal",
            "created_at": "2026-09-19T02:00:00Z",
            "updated_at": "2026-09-19T02:00:00Z",
        }
        self.reviews_builder = MockQueryBuilder(data=[row])

        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["rating"], 4)

    # --- 3. PATCH /api/v1/shops/{shop_id}/reviews/mine Tests ---

    def test_patch_review_empty_body_rejected_400(self):
        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("At least one field", response.json()["detail"])

    def test_patch_review_rating_null_rejected_422(self):
        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": None},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 422)

    def test_patch_review_content_null_clears_text(self):
        existing_row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 5,
            "content": "Old content",
        }
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"content": None},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.reviews_builder.last_updated, {"content": None})

    def test_patch_review_content_empty_string_clears_text(self):
        existing_row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 5,
        }
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"content": "    "},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.reviews_builder.last_updated, {"content": None})

    def test_patch_review_success_updates_rating_and_content(self):
        existing_row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 5,
            "content": "Old content",
        }
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": 3, "content": "Changed my mind, decent coffee."},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["rating"], 3)
        self.assertEqual(data["text"], "Changed my mind, decent coffee.")
        self.assertEqual(data["author"]["display_name"], "Maria Santos")
        self.assertTrue(data["is_edited"])
        self.assertIsNotNone(data["updated_at"])

    def test_patch_review_omitted_field_unchanged(self):
        existing_row = {
            "id": "22222222-3333-4444-5555-666666666666",
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "author_name": "Maria Santos",
            "rating": 5,
        }
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": 4},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.reviews_builder.last_updated, {"rating": 4})
        self.assertNotIn("content", self.reviews_builder.last_updated)

    def test_patch_review_blocked_when_shop_excluded(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "EXCLUDED"}])
        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": 4},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not approved for public discovery", response.json()["detail"])

    def test_patch_review_blocked_when_shop_pending_review(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "PENDING_REVIEW"}])
        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": 4},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("not approved for public discovery", response.json()["detail"])

    def test_patch_review_not_found_when_user_has_no_review(self):
        self.reviews_builder = MockQueryBuilder(data=[])
        response = self.client.patch(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            json={"rating": 4},
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "You have not reviewed this coffee shop.")

    # --- 4. DELETE /api/v1/shops/{shop_id}/reviews/mine Tests ---

    def test_delete_my_review_success_returns_200_message(self):
        existing_row = {"id": "22222222-3333-4444-5555-666666666666"}
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Review deleted successfully.")

    def test_delete_my_review_allowed_when_shop_excluded(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "EXCLUDED"}])
        existing_row = {"id": "22222222-3333-4444-5555-666666666666"}
        self.reviews_builder = MockQueryBuilder(data=[existing_row])

        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["message"], "Review deleted successfully.")

    def test_delete_my_review_not_found(self):
        self.reviews_builder = MockQueryBuilder(data=[])
        response = self.client.delete(
            f"/api/v1/shops/{self.shop_id}/reviews/mine",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "You have not reviewed this coffee shop.")

    # --- 5. GET /api/v1/shops/{shop_id}/reviews Fail-Closed Curation Tests ---

    def test_get_shop_reviews_returns_404_when_shop_excluded(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "EXCLUDED"}])
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Coffee shop not found.")

    def test_get_shop_reviews_returns_404_when_shop_pending_review(self):
        self.curation_builder = MockQueryBuilder(data=[{"status": "PENDING_REVIEW"}])
        response = self.client.get(
            f"/api/v1/shops/{self.shop_id}/reviews",
            headers=self.auth_headers,
        )
        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "Coffee shop not found.")


if __name__ == "__main__":
    unittest.main()
