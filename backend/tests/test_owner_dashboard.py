import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_service_role_supabase
from app.main import app
from app.schemas.curation import ShopEligibilityStatus
from app.services.curation import CurationService


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="owner@example.com",
        role="user",
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"full_name": "Verified Owner"}
        self.app_metadata = {"role": role}


class MockSupabaseTable:
    def __init__(self, data=None):
        self._data = data if data is not None else []
        self._action = "select"
        self._filters = []
        self._insert_payload = None
        self._update_payload = None
        self._limit = None

    def select(self, cols="*"):
        self._action = "select"
        self._filters = []
        self._limit = None
        return self

    def eq(self, col, val):
        self._filters.append((col, str(val)))
        return self

    def order(self, col, desc=False):
        return self

    def limit(self, count):
        self._limit = count
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

    def upsert(self, payload):
        self._action = "upsert"
        self._filters = []
        self._insert_payload = payload
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

        if self._action == "upsert":
            new_item = dict(self._insert_payload)
            # Find existing by id or shop_id
            match_idx = None
            for idx, r in enumerate(self._data):
                if ("id" in new_item and r.get("id") == new_item["id"]) or (
                    "shop_id" in new_item and r.get("shop_id") == new_item["shop_id"]
                ):
                    match_idx = idx
                    break
            if match_idx is not None:
                self._data[match_idx].update(new_item)
                mock_resp.data = [self._data[match_idx]]
            else:
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


class TestOwnerDashboardEndpoints(unittest.TestCase):
    def setUp(self):
        self.shop_a_id = str(uuid4())
        self.shop_b_id = str(uuid4())
        self.owner_id = "11111111-2222-3333-4444-555555555555"
        self.other_user_id = "22222222-3333-4444-5555-666666666666"
        self.curator_id = "33333333-4444-5555-6666-777777777777"

        self.owner_user = DummyUser(user_id=self.owner_id, email="owner@example.com")
        self.other_user = DummyUser(user_id=self.other_user_id, email="other@example.com")
        self.curator_user = DummyUser(user_id=self.curator_id, email="curator@lokal.ph", role="curator")

        self.shops_data = [
            {
                "id": self.shop_a_id,
                "name": "Artisan Brews A",
                "address": "100 Espresso Way",
                "latitude": 14.55,
                "longitude": 121.02,
                "rating": 4.6,
                "google_place_id": "place_a",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": self.shop_b_id,
                "name": "Artisan Brews B",
                "address": "200 Latte Blvd",
                "latitude": 14.56,
                "longitude": 121.03,
                "rating": 4.2,
                "google_place_id": "place_b",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            },
        ]

        self.curation_data = [
            {"shop_id": self.shop_a_id, "status": "APPROVED"},
            {"shop_id": self.shop_b_id, "status": "APPROVED"},
        ]

        self.claims_data = [
            {
                "id": str(uuid4()),
                "shop_id": self.shop_a_id,
                "user_id": self.owner_id,
                "status": "APPROVED",
                "claimant_name": "Verified Owner",
                "claimant_role": "Owner",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        self.reviews_data = [
            {
                "id": str(uuid4()),
                "shop_id": self.shop_a_id,
                "user_id": self.other_user_id,
                "author_name": "Maria C.",
                "rating": 5,
                "content": "Best flat white in town!",
                "source": "lokal",
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
        ]

        self.mock_supabase = MockSupabaseClient({
            "shops": self.shops_data,
            "shop_curation": self.curation_data,
            "shop_claims": self.claims_data,
            "reviews": self.reviews_data,
            "shop_curation_audit": [],
        })

        app.dependency_overrides[get_service_role_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_current_user] = lambda: self.owner_user
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    # =========================================================================
    # 1. Horizontal Privilege Escalation & Authorization
    # =========================================================================

    def test_owner_dashboard_unauthenticated_returns_401(self):
        app.dependency_overrides.pop(get_current_user, None)
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 401)

    def test_owner_dashboard_non_owner_returns_403(self):
        app.dependency_overrides[get_current_user] = lambda: self.other_user
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)
        self.assertIn("do not have approved owner permissions", res.json()["detail"])

    def test_owner_dashboard_pending_claim_returns_403(self):
        self.claims_data[0]["status"] = "PENDING"
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_owner_dashboard_rejected_claim_returns_403(self):
        self.claims_data[0]["status"] = "REJECTED"
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_owner_dashboard_revoked_claim_returns_403(self):
        self.claims_data[0]["status"] = "REVOKED"
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_owner_cannot_access_unclaimed_or_other_shop_returns_403(self):
        # Owner of Shop A attempts to view Shop B
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_b_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_owner_dashboard_success(self):
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["shop"]["id"], self.shop_a_id)
        self.assertEqual(data["shop"]["name"], "Artisan Brews A")
        self.assertEqual(data["claim"]["status"], "APPROVED")
        self.assertEqual(data["lokal_rating"], 5.0)
        self.assertEqual(data["lokal_reviews_count"], 1)
        self.assertEqual(len(data["recent_reviews"]), 1)
        self.assertEqual(data["recent_reviews"][0]["author"]["display_name"], "Maria C.")


    # =========================================================================
    # 2. Protected-Field Rejection Tests (extra="forbid")
    # =========================================================================

    def test_owner_patch_forbids_rating_field_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"rating": 5.0},
        )
        self.assertEqual(res.status_code, 422)
        errors = res.json()["detail"]
        self.assertTrue(any("extra_forbidden" in str(e) or "rating" in str(e) for e in errors))

    def test_owner_patch_forbids_google_place_id_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"google_place_id": "hacked_place_id"},
        )
        self.assertEqual(res.status_code, 422)

    def test_owner_patch_forbids_coordinates_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"latitude": 10.0, "longitude": 120.0},
        )
        self.assertEqual(res.status_code, 422)

    def test_owner_patch_forbids_curation_fields_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"curation_status": "APPROVED", "confidence": "HIGH"},
        )
        self.assertEqual(res.status_code, 422)

    def test_owner_patch_empty_payload_returns_400(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={},
        )
        self.assertEqual(res.status_code, 400)
        self.assertIn("At least one field must be provided", res.json()["detail"])

    def test_owner_patch_null_name_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"name": None},
        )
        self.assertEqual(res.status_code, 422)

    def test_owner_patch_blank_name_returns_422(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"name": "   "},
        )
        self.assertEqual(res.status_code, 422)

    def test_owner_patch_success_updates_name_and_address(self):
        res = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"name": "Artisan Roasters HQ", "address": "999 Coffee Blvd"},
        )
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertEqual(data["name"], "Artisan Roasters HQ")
        self.assertEqual(data["address"], "999 Coffee Blvd")

    # =========================================================================
    # 3. Curation Restoration Lifecycle Tests
    # =========================================================================

    def test_curation_exclusion_auto_revokes_claim_and_blocks_dashboard(self):
        """Item 4 verification: changing shop curation to EXCLUDED automatically revokes claim."""
        curation_service = CurationService()
        curation_service.override_curation(
            shop_id=self.shop_a_id,
            curator_id=self.curator_id,
            status_in=ShopEligibilityStatus.EXCLUDED,
            reason="Commercial chain identified.",
            supabase=self.mock_supabase,
        )

        # Claim must now be REVOKED
        self.assertEqual(self.claims_data[0]["status"], "REVOKED")
        self.assertIn("Automatically revoked", self.claims_data[0]["review_notes"])

        # Owner dashboard access must return 403 Forbidden
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_curation_restoration_to_approved_does_not_resurrect_ownership(self):
        """Item 4 core principle: when curation is restored to APPROVED, prior claim REMAINS REVOKED."""
        curation_service = CurationService()

        # Step 1: De-approve shop
        curation_service.override_curation(
            shop_id=self.shop_a_id,
            curator_id=self.curator_id,
            status_in=ShopEligibilityStatus.EXCLUDED,
            reason="Investigation pending.",
            supabase=self.mock_supabase,
        )
        self.assertEqual(self.claims_data[0]["status"], "REVOKED")

        # Step 2: Restore curation back to APPROVED
        curation_service.override_curation(
            shop_id=self.shop_a_id,
            curator_id=self.curator_id,
            status_in=ShopEligibilityStatus.APPROVED,
            reason="Cleared investigation.",
            supabase=self.mock_supabase,
        )

        # Verify shop is APPROVED in curation
        curation_record = next(c for c in self.curation_data if c["shop_id"] == self.shop_a_id)
        self.assertEqual(curation_record["status"], "APPROVED")

        # CRITICAL ASSERTION: The claim MUST STILL BE REVOKED!
        self.assertEqual(self.claims_data[0]["status"], "REVOKED")

        # Owner dashboard must STILL return 403 Forbidden!
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)
        self.assertIn("do not have approved owner permissions", res.json()["detail"])

        # Owner update attempt must ALSO return 403 Forbidden!
        res_patch = self.client.patch(
            f"/api/v1/owner/shops/{self.shop_a_id}",
            json={"name": "Attempted Unauthorized Name"},
        )
        self.assertEqual(res_patch.status_code, 403)


if __name__ == "__main__":
    unittest.main()
