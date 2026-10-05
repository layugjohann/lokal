import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient
from postgrest.exceptions import APIError

from app.api.deps import get_current_user, get_service_role_supabase
from app.main import app
from app.schemas.auth import UserResponse
from app.schemas.claim import ShopClaimStatus


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="claimant@example.com",
        role="user",
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"full_name": "Test Claimant"}
        self.app_metadata = {"role": role}


class MockSupabaseTable:
    def __init__(self, data=None):
        self._data = data if data is not None else []
        self._action = "select"
        self._filters = []
        self._insert_payload = None
        self._update_payload = None
        self._order_by = None
        self._limit = None
        self._range = None

    def select(self, cols="*"):
        self._action = "select"
        self._filters = []
        self._limit = None
        self._range = None
        return self

    def eq(self, col, val):
        self._filters.append((col, str(val)))
        return self

    def order(self, col, desc=False):
        self._order_by = (col, desc)
        return self

    def limit(self, count):
        self._limit = count
        return self

    def range(self, start, end):
        self._range = (start, end)
        return self

    def insert(self, payload):
        self._action = "insert"
        self._filters = []
        self._insert_payload = payload
        return self

    def update(self, payload):
        self._action = "update"
        self._filters = []
        self._update_payload = payload
        return self

    def delete(self):
        self._action = "delete"
        self._filters = []
        return self

    def execute(self):
        mock_resp = MagicMock()
        filtered = list(self._data)
        for col, val in self._filters:
            filtered = [r for r in filtered if str(r.get(col)) == str(val)]

        if self._action == "insert":
            new_item = dict(self._insert_payload)
            if "id" not in new_item:
                new_item["id"] = str(uuid4())
            if "created_at" not in new_item:
                new_item["created_at"] = datetime.now(timezone.utc).isoformat()
            if "updated_at" not in new_item:
                new_item["updated_at"] = datetime.now(timezone.utc).isoformat()
            self._data.append(new_item)
            mock_resp.data = [new_item]
            return mock_resp

        if self._action == "update":
            updated = []
            for item in filtered:
                item.update(self._update_payload)
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated.append(item)
            mock_resp.data = updated
            return mock_resp

        if self._action == "delete":
            mock_resp.data = list(filtered)
            return mock_resp

        if self._limit is not None:
            filtered = filtered[:self._limit]
        mock_resp.data = filtered
        return mock_resp


class MockSupabaseClient:
    def __init__(self, tables=None):
        self._table_data = tables if tables is not None else {}
        self._tables = {}

    def table(self, name):
        if name not in self._tables:
            data = self._table_data.setdefault(name, [])
            self._tables[name] = MockSupabaseTable(data)
        return self._tables[name]




class TestClaimEndpoints(unittest.TestCase):
    def setUp(self):
        self.shop_id = str(uuid4())
        self.user_id = "11111111-2222-3333-4444-555555555555"
        self.curator_id = "33333333-3333-3333-3333-333333333333"

        self.ordinary_user = DummyUser(user_id=self.user_id, email="claimant@example.com", role="user")
        self.curator_user = DummyUser(user_id=self.curator_id, email="curator@lokal.ph", role="curator")

        self.shops_data = [{
            "id": self.shop_id,
            "name": "Artisan Brews",
            "address": "123 Coffee Lane",
            "latitude": 14.55,
            "longitude": 121.02,
            "rating": 4.5,
            "google_place_id": "place_123",
        }]

        self.curation_data = [{
            "shop_id": self.shop_id,
            "status": "APPROVED",
        }]

        self.claims_data = []

        self.mock_supabase = MockSupabaseClient({
            "shops": self.shops_data,
            "shop_curation": self.curation_data,
            "shop_claims": self.claims_data,
        })


        app.dependency_overrides[get_service_role_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_current_user] = lambda: self.ordinary_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    # =========================================================================
    # 1. User Claim Submission
    # =========================================================================

    def test_submit_claim_success_returns_201_and_least_privilege_schema(self):
        payload = {
            "claimant_name": "Juan Dela Cruz",
            "claimant_phone": "+639171234567",
            "claimant_role": "Owner & Head Barista",
            "business_proof": "DTI Certificate #123456",
        }
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json=payload)
        self.assertEqual(res.status_code, 201)
        data = res.json()

        self.assertEqual(data["shop_id"], self.shop_id)
        self.assertEqual(data["status"], "PENDING")
        self.assertEqual(data["claimant_name"], "Juan Dela Cruz")
        self.assertEqual(data["claimant_role"], "Owner & Head Barista")
        self.assertIn("id", data)
        self.assertIn("created_at", data)
        self.assertIn("updated_at", data)

        # LEAST-PRIVILEGE DATA EXPOSURE ASSERTIONS
        self.assertNotIn("user_id", data, "Internal user_id must NOT be exposed in user-facing response")
        self.assertNotIn("claimant_phone", data, "Private phone should not be echoed back in public response")
        self.assertNotIn("business_proof", data, "Business proof should not be echoed back in public response")

    def test_submit_claim_unauthenticated_returns_401(self):
        app.dependency_overrides.pop(get_current_user, None)
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
            "claimant_name": "Test",
            "claimant_role": "Owner",
        })
        self.assertEqual(res.status_code, 401)

    def test_submit_claim_shop_not_found_returns_404(self):
        random_id = str(uuid4())
        res = self.client.post(f"/api/v1/shops/{random_id}/claim", json={
            "claimant_name": "Test",
            "claimant_role": "Owner",
        })
        self.assertEqual(res.status_code, 404)
        self.assertIn("Coffee shop not found", res.json()["detail"])

    def test_submit_claim_shop_not_approved_returns_400(self):
        self.curation_data[0]["status"] = "PENDING_REVIEW"
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
            "claimant_name": "Test",
            "claimant_role": "Owner",
        })
        self.assertEqual(res.status_code, 400)
        self.assertIn("Only approved coffee shops can be claimed", res.json()["detail"])

    def test_submit_claim_already_claimed_by_someone_else_returns_409(self):
        self.claims_data.append({
            "id": str(uuid4()),
            "shop_id": self.shop_id,
            "user_id": "99999999-9999-9999-9999-999999999999",
            "status": "APPROVED",
            "claimant_name": "Existing Owner",
            "claimant_role": "Owner",
        })
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
            "claimant_name": "New Claimant",
            "claimant_role": "Manager",
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already been claimed", res.json()["detail"])

    def test_submit_claim_user_already_has_pending_claim_returns_409(self):
        self.claims_data.append({
            "id": str(uuid4()),
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Same User",
            "claimant_role": "Manager",
        })
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
            "claimant_name": "Same User",
            "claimant_role": "Manager",
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already have a pending claim", res.json()["detail"])

    def test_submit_claim_user_already_owner_returns_409(self):
        self.claims_data.append({
            "id": str(uuid4()),
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "APPROVED",
            "claimant_name": "Current Owner",
            "claimant_role": "Owner",
        })
        res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
            "claimant_name": "Current Owner",
            "claimant_role": "Owner",
        })
        self.assertEqual(res.status_code, 409)
        self.assertIn("already the verified owner", res.json()["detail"])

    def test_submit_claim_database_unique_violation_returns_409(self):
        with patch.object(self.mock_supabase.table("shop_claims"), "insert") as mock_insert:
            mock_insert.return_value.execute.side_effect = APIError({
                "message": "duplicate key value violates unique constraint",
                "code": "23505",
            })
            res = self.client.post(f"/api/v1/shops/{self.shop_id}/claim", json={
                "claimant_name": "Race User",
                "claimant_role": "Owner",
            })
            self.assertEqual(res.status_code, 409)
            self.assertIn("conflicting claim already exists", res.json()["detail"])

    # =========================================================================
    # 2. User Claim Status & Listing
    # =========================================================================

    def test_get_shop_claim_status_unclaimed_returns_null(self):
        res = self.client.get(f"/api/v1/shops/{self.shop_id}/claim")
        self.assertEqual(res.status_code, 200)
        self.assertIsNone(res.json())

    def test_get_shop_claim_status_claimed_returns_claim(self):
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Claimant",
            "claimant_role": "Owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        res = self.client.get(f"/api/v1/shops/{self.shop_id}/claim")
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["id"], claim_id)
        self.assertEqual(data["status"], "PENDING")
        self.assertNotIn("user_id", data)

    def test_list_my_claims_returns_caller_claims(self):
        self.claims_data.append({
            "id": str(uuid4()),
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Claimant",
            "claimant_role": "Owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
        res = self.client.get("/api/v1/claims/mine")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        self.assertNotIn("user_id", items[0])

    # =========================================================================
    # 3. Curator Review Boundaries
    # =========================================================================

    def test_curator_endpoints_forbidden_for_ordinary_user(self):
        claim_id = str(uuid4())
        # List claims
        res = self.client.get("/api/v1/claims")
        self.assertEqual(res.status_code, 403)
        # Get claim
        res = self.client.get(f"/api/v1/claims/{claim_id}")
        self.assertEqual(res.status_code, 403)
        # Approve
        res = self.client.post(f"/api/v1/claims/{claim_id}/approve", json={})
        self.assertEqual(res.status_code, 403)
        # Reject
        res = self.client.post(f"/api/v1/claims/{claim_id}/reject", json={})
        self.assertEqual(res.status_code, 403)
        # Revoke
        res = self.client.post(f"/api/v1/claims/{claim_id}/revoke", json={})
        self.assertEqual(res.status_code, 403)

    def test_curator_list_and_detail_claims_includes_audit_info(self):
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Applicant",
            "claimant_phone": "0917-000-0000",
            "claimant_role": "Owner",
            "business_proof": "Official Permit #999",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        res = self.client.get("/api/v1/claims")
        self.assertEqual(res.status_code, 200)
        items = res.json()
        self.assertEqual(len(items), 1)
        # CURATOR EXPOSURE: user_id, claimant_phone, and business_proof ARE included
        self.assertEqual(items[0]["user_id"], self.user_id)
        self.assertEqual(items[0]["claimant_phone"], "0917-000-0000")
        self.assertEqual(items[0]["business_proof"], "Official Permit #999")

        # Detail route
        res_detail = self.client.get(f"/api/v1/claims/{claim_id}")
        self.assertEqual(res_detail.status_code, 200)
        self.assertEqual(res_detail.json()["id"], claim_id)
        self.assertEqual(res_detail.json()["user_id"], self.user_id)

    def test_curator_approve_claim_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Applicant",
            "claimant_role": "Owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        res = self.client.post(f"/api/v1/claims/{claim_id}/approve", json={"review_notes": "Permit verified."})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "APPROVED")
        self.assertEqual(data["curator_id"], self.curator_id)
        self.assertEqual(data["review_notes"], "Permit verified.")
        self.assertIsNotNone(data["reviewed_at"])

    def test_curator_approve_claim_when_already_approved_owner_returns_409(self):
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        # Existing approved claim
        self.claims_data.append({
            "id": str(uuid4()),
            "shop_id": self.shop_id,
            "user_id": "88888888-8888-8888-8888-888888888888",
            "status": "APPROVED",
            "claimant_name": "First Owner",
            "claimant_role": "Owner",
        })
        # Competing pending claim
        competing_claim_id = str(uuid4())
        self.claims_data.append({
            "id": competing_claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Second Claimant",
            "claimant_role": "Manager",
        })

        res = self.client.post(f"/api/v1/claims/{competing_claim_id}/approve", json={})
        self.assertEqual(res.status_code, 409)
        self.assertIn("already has an approved owner", res.json()["detail"])

    def test_curator_approve_claim_concurrent_race_code_23505_returns_409(self):
        """Item 2 verification: DB boundary concurrency race (code 23505) maps to HTTP 409 Conflict, not 500."""
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Racer",
            "claimant_role": "Owner",
        })

        with patch.object(self.mock_supabase.table("shop_claims"), "update") as mock_update:
            mock_update.return_value.eq.return_value.execute.side_effect = APIError({
                "message": "duplicate key value violates unique constraint idx_unique_approved_claim_per_shop",
                "code": "23505",
            })
            res = self.client.post(f"/api/v1/claims/{claim_id}/approve", json={})
            self.assertEqual(res.status_code, 409)
            self.assertIn("already has an approved owner", res.json()["detail"])

    def test_curator_reject_claim_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "PENDING",
            "claimant_name": "Applicant",
            "claimant_role": "Owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        res = self.client.post(f"/api/v1/claims/{claim_id}/reject", json={"review_notes": "Unverifiable affiliation."})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "REJECTED")
        self.assertEqual(data["review_notes"], "Unverifiable affiliation.")

    def test_curator_revoke_claim_success(self):
        app.dependency_overrides[get_current_user] = lambda: self.curator_user
        claim_id = str(uuid4())
        self.claims_data.append({
            "id": claim_id,
            "shop_id": self.shop_id,
            "user_id": self.user_id,
            "status": "APPROVED",
            "claimant_name": "Applicant",
            "claimant_role": "Owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })

        res = self.client.post(f"/api/v1/claims/{claim_id}/revoke", json={"review_notes": "Business sold."})
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["status"], "REVOKED")
        self.assertEqual(data["review_notes"], "Business sold.")


if __name__ == "__main__":
    unittest.main()
