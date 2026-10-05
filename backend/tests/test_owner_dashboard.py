import os
import sys
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_service_role_supabase
from app.main import app
from app.schemas.curation import CurationConfidence, ShopEligibilityStatus
from app.services.curation import CurationService
from app.services.curation.classifier import ClassificationDecision


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
    def __init__(self, data=None, name=None, client=None):
        self._data = data if data is not None else []
        self._name = name
        self._client = client
        self._action = "select"
        self._filters = []
        self._insert_payload = None
        self._update_payload = None
        self._order_by = None
        self._limit = None

    def select(self, cols="*"):
        self._action = "select"
        self._filters = []
        self._limit = None
        self._order_by = None
        return self

    def eq(self, col, val):
        self._filters.append((col, val))
        return self

    def order(self, col, desc=False):
        self._order_by = (col, desc)
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

    def _fire_curation_demotion_trigger(self, shop_id, old_status, new_status):
        if old_status == "APPROVED" and new_status != "APPROVED":
            if self._client and getattr(self._client, "simulate_atomic_failure", False):
                raise Exception("Database atomic failure in claim revocation trigger")
            if self._client and "shop_claims" in self._client._table_data:
                for claim in self._client._table_data["shop_claims"]:
                    if str(claim.get("shop_id")) == str(shop_id) and claim.get("status") == "APPROVED":
                        claim["status"] = "REVOKED"
                        claim["review_notes"] = f"Automatically revoked due to coffee shop curation status change to {new_status}."
                        claim["updated_at"] = datetime.now(timezone.utc).isoformat()

    def execute(self):
        mock_resp = MagicMock()
        filtered = list(self._data)
        for col, val in self._filters:
            if isinstance(val, bool):
                filtered = [r for r in filtered if bool(r.get(col, False)) == val]
            else:
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
                old_row = self._data[match_idx]
                old_status = old_row.get("status")
                new_status = new_item.get("status")
                shop_id = old_row.get("shop_id") or new_item.get("shop_id")
                if self._name == "shop_curation":
                    self._fire_curation_demotion_trigger(shop_id, old_status, new_status)
                old_row.update(new_item)
                mock_resp.data = [old_row]
            else:
                self._data.append(new_item)
                mock_resp.data = [new_item]
            return mock_resp

        if self._action == "update":
            if self._name == "shop_curation":
                new_status = self._update_payload.get("status")
                for item in filtered:
                    old_status = item.get("status")
                    shop_id = item.get("shop_id")
                    self._fire_curation_demotion_trigger(shop_id, old_status, new_status)
            updated = []
            for item in filtered:
                item.update(self._update_payload)
                item["updated_at"] = datetime.now(timezone.utc).isoformat()
                updated.append(item)
            mock_resp.data = updated
            return mock_resp

        if self._order_by is not None:
            col, desc = self._order_by
            filtered.sort(key=lambda r: str(r.get(col, "")), reverse=desc)

        if self._limit is not None:
            filtered = filtered[:self._limit]
        mock_resp.data = filtered
        return mock_resp


class MockSupabaseClient:
    def __init__(self, tables=None):
        self._table_data = tables if tables is not None else {}
        self._tables = {}
        self.simulate_atomic_failure = False

    def table(self, name):
        if name not in self._tables:
            data = self._table_data.setdefault(name, [])
            self._tables[name] = MockSupabaseTable(data, name=name, client=self)
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

    def test_automated_evaluate_shop_demotion_auto_revokes_claim(self):
        """Automated evaluate_shop demoting an approved shop atomically revokes approved claim."""
        import asyncio
        curation_service = CurationService()
        curation_service.classifier.classify = AsyncMock(
            return_value=ClassificationDecision(
                status=ShopEligibilityStatus.EXCLUDED,
                confidence=CurationConfidence.HIGH,
                location_count=6,
                evidence_source="places",
                reason="Chain detected.",
                qualifying_locations=[],
            )
        )
        asyncio.run(curation_service.evaluate_shop(
            shop_id=self.shop_a_id,
            supabase=self.mock_supabase,
        ))

        # Claim must now be REVOKED via atomic trigger
        self.assertEqual(self.claims_data[0]["status"], "REVOKED")
        self.assertIn("Automatically revoked", self.claims_data[0]["review_notes"])

        # Owner dashboard access must return 403 Forbidden
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 403)

    def test_atomic_curation_demotion_failure_protects_against_inconsistency(self):
        """Simulated atomic database failure leaves curation APPROVED and claim APPROVED (neither commits)."""
        curation_service = CurationService()
        self.mock_supabase.simulate_atomic_failure = True

        with self.assertRaises(HTTPException) as ctx:
            curation_service.override_curation(
                shop_id=self.shop_a_id,
                curator_id=self.curator_id,
                status_in=ShopEligibilityStatus.EXCLUDED,
                reason="Failure test.",
                supabase=self.mock_supabase,
            )
        self.assertEqual(ctx.exception.status_code, 500)

        # Invariant: Neither commits! Curation remains APPROVED and claim remains APPROVED
        curation_record = next(c for c in self.curation_data if c["shop_id"] == self.shop_a_id)
        self.assertEqual(curation_record["status"], "APPROVED")
        self.assertEqual(self.claims_data[0]["status"], "APPROVED")

        # Owner dashboard remains accessible because status was not corrupted
        self.mock_supabase.simulate_atomic_failure = False
        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 200)

    # =========================================================================
    # 4. Review Aggregation and Bounded Retrieval Tests
    # =========================================================================

    def test_dashboard_metrics_with_more_than_twenty_reviews(self):
        """Item 2: Aggregate count and average reflect >20 reviews while recent reviews remain bounded to 5."""
        self.reviews_data.clear()
        # 15 reviews with 5.0, 10 reviews with 4.0 -> total 25 reviews, sum = 115, avg = 4.60
        for i in range(15):
            self.reviews_data.append({
                "id": str(uuid4()),
                "shop_id": self.shop_a_id,
                "user_id": str(uuid4()),
                "author_name": f"Five Star User {i}",
                "rating": 5,
                "content": f"Great coffee #{i}",
                "source": "lokal",
                "created_at": f"2026-09-0{i%9+1}T10:00:00Z",
                "updated_at": f"2026-09-0{i%9+1}T10:00:00Z",
            })
        for i in range(10):
            self.reviews_data.append({
                "id": str(uuid4()),
                "shop_id": self.shop_a_id,
                "user_id": str(uuid4()),
                "author_name": f"Four Star User {i}",
                "rating": 4,
                "content": f"Good coffee #{i}",
                "source": "lokal",
                "created_at": f"2026-09-1{i%9+1}T10:00:00Z",
                "updated_at": f"2026-09-1{i%9+1}T10:00:00Z",
            })

        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # All 25 reviews must be counted
        self.assertEqual(data["lokal_reviews_count"], 25)
        self.assertEqual(data["lokal_rating"], 4.6)

        # Recent reviews must be strictly bounded to at most 5
        self.assertEqual(len(data["recent_reviews"]), 5)

    def test_dashboard_metrics_ignores_null_and_out_of_range_ratings(self):
        """Item 2: Null, non-numeric, and out-of-range (<1, >5) ratings do not crash dashboard."""
        self.reviews_data.clear()
        # Malformed/invalid reviews
        self.reviews_data.extend([
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": None, "content": "No rating", "source": "lokal", "created_at": "2026-09-01T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": 0, "content": "Zero stars", "source": "lokal", "created_at": "2026-09-02T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": -1, "content": "Negative rating", "source": "lokal", "created_at": "2026-09-03T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": 6, "content": "Six stars", "source": "lokal", "created_at": "2026-09-04T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": "5_stars", "content": "String rating", "source": "lokal", "created_at": "2026-09-05T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": True, "content": "Boolean rating", "source": "lokal", "created_at": "2026-09-06T10:00:00Z"},
            # Valid reviews: one 4.0 and one 5.0 -> count = 2, avg = 4.5
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": 4, "content": "Valid four", "source": "lokal", "created_at": "2026-09-07T10:00:00Z"},
            {"id": str(uuid4()), "shop_id": self.shop_a_id, "rating": 5, "content": "Valid five", "source": "lokal", "created_at": "2026-09-08T10:00:00Z"},
        ])

        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        # Only the 2 valid reviews are counted and averaged
        self.assertEqual(data["lokal_reviews_count"], 2)
        self.assertEqual(data["lokal_rating"], 4.5)
        self.assertEqual(len(data["recent_reviews"]), 2)

    def test_dashboard_recent_reviews_bounded_to_top_five(self):
        """Item 2: When multiple valid reviews exist, recent reviews strictly populates top 5 ordered by created_at desc."""
        self.reviews_data.clear()
        for i in range(1, 9):
            self.reviews_data.append({
                "id": str(uuid4()),
                "shop_id": self.shop_a_id,
                "author_name": f"User {i}",
                "rating": 5,
                "content": f"Review {i}",
                "source": "lokal",
                "created_at": f"2026-09-0{i}T12:00:00Z",
                "updated_at": f"2026-09-0{i}T12:00:00Z",
            })

        res = self.client.get(f"/api/v1/owner/shops/{self.shop_a_id}/dashboard")
        self.assertEqual(res.status_code, 200)
        data = res.json()

        self.assertEqual(data["lokal_reviews_count"], 8)
        self.assertEqual(len(data["recent_reviews"]), 5)
        # Verify the top 5 are in descending created_at order (most recent first: Review 8, 7, 6, 5, 4)
        review_texts = [r["text"] for r in data["recent_reviews"]]
        self.assertEqual(review_texts, ["Review 8", "Review 7", "Review 6", "Review 5", "Review 4"])


if __name__ == "__main__":
    unittest.main()
