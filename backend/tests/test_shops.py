import os
import sys
import unittest
from unittest.mock import MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import HTTPException
from fastapi.testclient import TestClient
from postgrest.exceptions import APIError
from supabase_auth.errors import AuthApiError

from app.main import app
from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase
from app.schemas.auth import UserResponse


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
        self.last_inserted = None
        self.last_updated = None
        self.last_eq = None
        self.last_range = None
        self.mock_execute = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = data
        self.mock_execute.return_value = mock_resp

    def insert(self, payload):
        self.last_inserted = payload
        return self

    def select(self, cols="*"):
        return self

    def update(self, payload):
        self.last_updated = payload
        return self

    def delete(self):
        return self

    def eq(self, col, val):
        self.last_eq = (col, val)
        return self

    def order(self, col):
        return self

    def range(self, start, end):
        self.last_range = (start, end)
        return self

    def execute(self):
        return self.mock_execute()


class TestShopEndpoints(unittest.TestCase):
    def setUp(self):
        self.mock_supabase = MagicMock()
        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        self.client = TestClient(app)
        self.auth_headers = {"Authorization": "Bearer valid-mock-token"}
        # Default mock auth user response
        self.mock_supabase.auth.get_user.return_value = DummyUserResponse()


        self.sample_shop = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Kape Lokal",
            "address": "123 Katipunan Ave, Quezon City",
            "latitude": 14.6488,
            "longitude": 121.0734,
            "rating": 4.75,
            "google_place_id": "ChIJN1t_tDeuEmsRUsoyG83frY4",
            "created_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:00:00Z",
        }

    def tearDown(self):
        app.dependency_overrides.clear()

    # --- Authentication Rejection Tests ---
    def test_unauthenticated_requests_rejected(self):
        shop_id = "123e4567-e89b-12d3-a456-426614174000"

        # POST /api/v1/shops without auth
        resp = self.client.post("/api/v1/shops", json={"name": "Cafe", "latitude": 14.5, "longitude": 121.0})
        self.assertEqual(resp.status_code, 401)

        # GET /api/v1/shops without auth
        resp = self.client.get("/api/v1/shops")
        self.assertEqual(resp.status_code, 401)

        # GET /api/v1/shops/{id} without auth
        resp = self.client.get(f"/api/v1/shops/{shop_id}")
        self.assertEqual(resp.status_code, 401)

        # PATCH /api/v1/shops/{id} without auth
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"name": "New Name"})
        self.assertEqual(resp.status_code, 401)

        # DELETE /api/v1/shops/{id} without auth
        resp = self.client.delete(f"/api/v1/shops/{shop_id}")
        self.assertEqual(resp.status_code, 401)

    def test_invalid_token_rejected(self):
        self.mock_supabase.auth.get_user.side_effect = AuthApiError("Invalid token", 401, "invalid_jwt")
        resp = self.client.get("/api/v1/shops", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 401)

    # --- Create Coffee Shop Tests ---
    def test_create_shop_success(self):
        builder = MockQueryBuilder(data=[self.sample_shop])
        self.mock_supabase.table.return_value = builder

        payload = {
            "name": "  Kape Lokal  ",
            "address": "  123 Katipunan Ave, Quezon City  ",
            "latitude": 14.6488,
            "longitude": 121.0734,
            "rating": 4.75,
            "google_place_id": "  ChIJN1t_tDeuEmsRUsoyG83frY4  ",
        }
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 201)
        data = resp.json()
        self.assertEqual(data["id"], self.sample_shop["id"])
        self.assertEqual(data["name"], "Kape Lokal")
        self.assertEqual(data["latitude"], 14.6488)
        self.assertEqual(data["longitude"], 121.0734)

        self.mock_supabase.table.assert_called_with("shops")
        # Verify fields were trimmed in payload sent to insert
        self.assertEqual(builder.last_inserted["name"], "Kape Lokal")
        self.assertEqual(builder.last_inserted["address"], "123 Katipunan Ave, Quezon City")
        self.assertEqual(builder.last_inserted["google_place_id"], "ChIJN1t_tDeuEmsRUsoyG83frY4")

    def test_create_shop_minimal_fields_success(self):
        minimal_shop = {
            "id": "123e4567-e89b-12d3-a456-426614174000",
            "name": "Minimalist Cafe",
            "address": None,
            "latitude": 14.5,
            "longitude": 121.0,
            "rating": None,
            "google_place_id": None,
            "created_at": "2026-09-01T08:00:00Z",
            "updated_at": "2026-09-01T08:00:00Z",
        }
        builder = MockQueryBuilder(data=[minimal_shop])
        self.mock_supabase.table.return_value = builder

        payload = {
            "name": "Minimalist Cafe",
            "latitude": 14.5,
            "longitude": 121.0,
        }
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.json()["name"], "Minimalist Cafe")

    def test_create_shop_validation_missing_name(self):
        payload = {"latitude": 14.5, "longitude": 121.0}
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_create_shop_validation_blank_name(self):
        payload = {"name": "   ", "latitude": 14.5, "longitude": 121.0}
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_create_shop_validation_invalid_coordinates(self):
        # Latitude out of range (> 90)
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": 91.0, "longitude": 121.0},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Latitude out of range (< -90)
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": -91.0, "longitude": 121.0},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Longitude out of range (> 180)
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": 14.5, "longitude": 181.0},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Longitude out of range (< -180)
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": 14.5, "longitude": -181.0},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_create_shop_validation_invalid_rating(self):
        # Rating > 5.0
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": 14.5, "longitude": 121.0, "rating": 5.5},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

        # Rating < 0.0
        resp = self.client.post(
            "/api/v1/shops",
            json={"name": "Test Cafe", "latitude": 14.5, "longitude": 121.0, "rating": -1.0},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 422)

    def test_create_shop_duplicate_google_place_id(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "duplicate key value violates unique constraint", "code": "23505", "details": "Key (google_place_id)=(xyz) already exists."}
        )
        self.mock_supabase.table.return_value = builder

        payload = {
            "name": "Duplicate Cafe",
            "latitude": 14.5,
            "longitude": 121.0,
            "google_place_id": "already_existing_id",
        }
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 409)
        self.assertIn("already exists", resp.json()["detail"])

    def test_create_shop_database_error(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "relation not found", "code": "42P01", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        payload = {"name": "Test Cafe", "latitude": 14.5, "longitude": 121.0}
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("A database error occurred", resp.json()["detail"])


    def test_create_shop_empty_data_returned(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        payload = {"name": "Test Cafe", "latitude": 14.5, "longitude": 121.0}
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)

    # --- List Coffee Shops Tests ---
    def test_list_shops_success(self):
        builder = MockQueryBuilder(data=[self.sample_shop])
        self.mock_supabase.table.return_value = builder

        resp = self.client.get("/api/v1/shops", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["id"], self.sample_shop["id"])
        self.assertEqual(builder.last_range, (0, 49))

    def test_list_shops_pagination(self):
        builder = MockQueryBuilder(data=[self.sample_shop])
        self.mock_supabase.table.return_value = builder

        resp = self.client.get("/api/v1/shops?limit=10&offset=20", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(builder.last_range, (20, 29))

    def test_list_shops_invalid_pagination(self):
        # limit < 1
        resp = self.client.get("/api/v1/shops?limit=0", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

        # limit > 100
        resp = self.client.get("/api/v1/shops?limit=101", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

        # offset < 0
        resp = self.client.get("/api/v1/shops?offset=-1", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_list_shops_database_error(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "connection terminated", "code": "08006", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        resp = self.client.get("/api/v1/shops", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("A database error occurred", resp.json()["detail"])

    # --- Retrieve Coffee Shop by ID Tests ---
    def test_get_shop_by_id_success(self):
        builder = MockQueryBuilder(data=[self.sample_shop])
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.get(f"/api/v1/shops/{shop_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["id"], shop_id)
        self.assertEqual(builder.last_eq, ("id", shop_id))

    def test_get_shop_by_id_database_error(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "connection reset", "code": "08006", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.get(f"/api/v1/shops/{shop_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("A database error occurred", resp.json()["detail"])


    def test_get_shop_by_id_not_found(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        random_id = str(uuid4())
        resp = self.client.get(f"/api/v1/shops/{random_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Coffee shop not found", resp.json()["detail"])

    def test_get_shop_by_id_malformed_uuid(self):
        resp = self.client.get("/api/v1/shops/invalid-uuid-format", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    # --- Update Coffee Shop Tests (PATCH) ---
    def test_update_shop_success(self):
        updated_shop = dict(self.sample_shop)
        updated_shop["name"] = "Updated Kape"
        updated_shop["rating"] = 4.90

        builder = MockQueryBuilder(data=[updated_shop])
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        payload = {"name": "  Updated Kape  ", "rating": 4.90}
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["name"], "Updated Kape")
        self.assertEqual(data["rating"], 4.90)
        self.assertEqual(builder.last_updated, {"name": "Updated Kape", "rating": 4.90})

    def test_update_shop_empty_payload_rejected(self):
        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 400)
        self.assertIn("At least one field must be provided for update", resp.json()["detail"])

    def test_update_shop_null_name_rejected(self):
        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"name": None}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_update_shop_null_latitude_rejected(self):
        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"latitude": None}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_update_shop_null_longitude_rejected(self):
        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"longitude": None}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_update_shop_blank_name_rejected(self):
        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"name": "   "}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)


    def test_update_shop_not_found(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        random_id = str(uuid4())
        resp = self.client.patch(f"/api/v1/shops/{random_id}", json={"name": "New Name"}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Coffee shop not found", resp.json()["detail"])

    def test_update_shop_duplicate_google_place_id(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "duplicate key value violates unique constraint", "code": "23505", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.patch(
            f"/api/v1/shops/{shop_id}",
            json={"google_place_id": "already_taken_id"},
            headers=self.auth_headers,
        )
        self.assertEqual(resp.status_code, 409)
        self.assertIn("already exists", resp.json()["detail"])

    def test_update_shop_database_error(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "transaction aborted", "code": "25P02", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.patch(f"/api/v1/shops/{shop_id}", json={"name": "New Name"}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("A database error occurred", resp.json()["detail"])

    def test_update_shop_malformed_uuid(self):
        resp = self.client.patch("/api/v1/shops/not-a-valid-uuid", json={"name": "Cafe"}, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    # --- Delete Coffee Shop Tests ---
    def test_delete_shop_success(self):
        builder = MockQueryBuilder(data=[self.sample_shop])
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.delete(f"/api/v1/shops/{shop_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"message": "Coffee shop deleted successfully."})
        self.assertEqual(builder.last_eq, ("id", shop_id))

    def test_delete_shop_not_found(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        random_id = str(uuid4())
        resp = self.client.delete(f"/api/v1/shops/{random_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 404)
        self.assertIn("Coffee shop not found", resp.json()["detail"])

    def test_delete_shop_malformed_uuid(self):
        resp = self.client.delete("/api/v1/shops/bad-uuid", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 422)

    def test_delete_shop_database_error(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = APIError(
            {"message": "disk full", "code": "53100", "details": None}
        )
        self.mock_supabase.table.return_value = builder

        shop_id = self.sample_shop["id"]
        resp = self.client.delete(f"/api/v1/shops/{shop_id}", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("A database error occurred", resp.json()["detail"])


    def test_shops_unexpected_exception_generic_message(self):
        builder = MockQueryBuilder()
        builder.mock_execute.side_effect = RuntimeError("Sensitive DB internal error")
        self.mock_supabase.table.return_value = builder

        payload = {"name": "Test Cafe", "latitude": 14.5, "longitude": 121.0}
        resp = self.client.post("/api/v1/shops", json=payload, headers=self.auth_headers)
        self.assertEqual(resp.status_code, 500)
        self.assertEqual(resp.json()["detail"], "An unexpected error occurred while processing the request.")
        self.assertNotIn("Sensitive DB internal error", resp.text)

    # --- Unconfigured Supabase Dependency Test ---
    def test_shops_supabase_unconfigured(self):
        def raise_503():
            raise HTTPException(status_code=503, detail="Supabase not configured.")

        app.dependency_overrides[get_authenticated_supabase] = raise_503
        resp = self.client.get("/api/v1/shops", headers=self.auth_headers)
        self.assertEqual(resp.status_code, 503)


class TestScopedSupabaseClient(unittest.TestCase):
    def test_create_scoped_client_sets_caller_jwt_and_preserves_shared(self):
        from unittest.mock import patch
        from app.core.supabase import create_scoped_supabase_client, get_supabase_client
        from app.core.config import settings

        with patch.object(settings, "SUPABASE_URL", "https://test.supabase.co"), \
             patch.object(settings, "SUPABASE_ANON_KEY", "anon-key-test"):
            shared_client = get_supabase_client()
            scoped_client = create_scoped_supabase_client("custom-caller-token-123")

            self.assertNotEqual(id(shared_client), id(scoped_client))
            self.assertEqual(scoped_client.postgrest.headers.get("authorization"), "Bearer custom-caller-token-123")
            self.assertEqual(shared_client.postgrest.headers.get("authorization"), "Bearer anon-key-test")


if __name__ == '__main__':
    unittest.main()

