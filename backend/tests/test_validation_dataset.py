import math
import os
import sys
import unittest
from uuid import UUID

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.fixtures.validation_dataset import (
    CURATOR_USER_ID,
    FIXTURE_CLAIMS,
    FIXTURE_CURATION_AUDITS,
    FIXTURE_FAVORITES,
    FIXTURE_REVIEWS,
    FIXTURE_SHOPS,
    FIXTURE_USERS,
    OWNER_USER_ID,
)


def haversine_distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate distance in meters between two coordinates using the Haversine formula."""
    r = 6371000.0  # Earth radius in meters
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


class TestValidationDataset(unittest.TestCase):
    """Offline unit tests validating structure, integrity, and safety of validation dataset fixtures."""

    def test_entity_counts(self):
        """Assert exact entity counts matching the approved Issue #49 plan."""
        self.assertEqual(len(FIXTURE_SHOPS), 23)
        self.assertEqual(len(FIXTURE_REVIEWS), 23)
        self.assertEqual(len(FIXTURE_USERS), 10)
        self.assertEqual(len(FIXTURE_FAVORITES), 8)
        self.assertEqual(len(FIXTURE_CLAIMS), 1)
        self.assertEqual(len(FIXTURE_CURATION_AUDITS), 23)

        approved_shops = [s for s in FIXTURE_SHOPS if s.curation_status == "APPROVED"]
        excluded_shops = [s for s in FIXTURE_SHOPS if s.curation_status == "EXCLUDED"]
        pending_shops = [s for s in FIXTURE_SHOPS if s.curation_status == "PENDING_REVIEW"]

        self.assertEqual(len(approved_shops), 18)
        self.assertEqual(len(excluded_shops), 3)
        self.assertEqual(len(pending_shops), 2)

        # 12 Real Approved + 6 Synthetic Approved
        real_approved = [s for s in approved_shops if s.is_real]
        synthetic_approved = [s for s in approved_shops if not s.is_real]
        self.assertEqual(len(real_approved), 12)
        self.assertEqual(len(synthetic_approved), 6)

    def test_coordinate_bounds(self):
        """Verify that all coordinates fall within valid geographic bounds."""
        for shop in FIXTURE_SHOPS:
            self.assertGreaterEqual(shop.latitude, -90.0, f"{shop.name} latitude out of bounds")
            self.assertLessEqual(shop.latitude, 90.0, f"{shop.name} latitude out of bounds")
            self.assertGreaterEqual(shop.longitude, -180.0, f"{shop.name} longitude out of bounds")
            self.assertLessEqual(shop.longitude, 180.0, f"{shop.name} longitude out of bounds")

            # Must be in Metro Manila bounding box (14.2 to 14.8 N, 120.8 to 121.2 E)
            self.assertTrue(14.2 <= shop.latitude <= 14.8, f"{shop.name} outside Metro Manila latitude")
            self.assertTrue(120.8 <= shop.longitude <= 121.2, f"{shop.name} outside Metro Manila longitude")

    def test_rating_bounds_and_storage_compliance(self):
        """Assert provider-derived ratings are NOT persisted for real shops, and synthetic ratings are valid."""
        for shop in FIXTURE_SHOPS:
            if shop.is_real:
                # Real shops must not persist unrefreshed Google rating data
                self.assertIsNone(shop.rating, f"Real shop {shop.name} must not persist provider rating")
            else:
                # Synthetic shops may have null or 0.0-5.0 synthetic rating
                if shop.rating is not None:
                    self.assertGreaterEqual(shop.rating, 0.0)
                    self.assertLessEqual(shop.rating, 5.0)

    def test_curation_policy_compliance(self):
        """Verify that curation classifications strictly respect LOKAL's 5-location threshold."""
        for shop in FIXTURE_SHOPS:
            if shop.curation_status == "APPROVED":
                self.assertIsNotNone(shop.branch_count)
                self.assertLessEqual(shop.branch_count, 5, f"{shop.name} has >5 branches but is APPROVED")
                self.assertEqual(shop.confidence, "HIGH")
            elif shop.curation_status == "EXCLUDED":
                self.assertIsNotNone(shop.branch_count)
                self.assertGreaterEqual(shop.branch_count, 6, f"{shop.name} has <6 branches but is EXCLUDED")
                self.assertEqual(shop.confidence, "HIGH")
            elif shop.curation_status == "PENDING_REVIEW":
                self.assertIsNone(shop.branch_count)
                self.assertEqual(shop.confidence, "LOW")

    def test_review_integrity_and_isolation(self):
        """Verify that synthetic reviews are isolated strictly to synthetic [Test] shops."""
        real_shop_ids = {s.id for s in FIXTURE_SHOPS if s.is_real}
        synthetic_shop_ids = {s.id for s in FIXTURE_SHOPS if not s.is_real}

        for review in FIXTURE_REVIEWS:
            # Reviews must NEVER be attached to real businesses
            self.assertNotIn(
                review.shop_id,
                real_shop_ids,
                f"Review {review.id} was attached to real shop {review.shop_id}",
            )
            self.assertIn(
                review.shop_id,
                synthetic_shop_ids,
                f"Review {review.id} was not attached to a synthetic shop",
            )
            self.assertEqual(review.source, "lokal")
            self.assertTrue(1 <= review.rating <= 5)
            self.assertTrue(review.content.startswith("[Validation Test]"))

        # Verify single review per user per shop uniqueness (uq_reviews_user_shop)
        seen_pairs = set()
        for review in FIXTURE_REVIEWS:
            pair = (review.user_id, review.shop_id)
            self.assertNotIn(pair, seen_pairs, f"Duplicate review for user/shop pair {pair}")
            seen_pairs.add(pair)

        # Verify at least one review has updated_at > created_at for (Edited) UI indicator testing
        edited_reviews = [r for r in FIXTURE_REVIEWS if r.updated_at > r.created_at]
        self.assertGreaterEqual(len(edited_reviews), 1)

    def test_controlled_user_accounts(self):
        """Assert user personas use @lokal.dev and unique deterministic UUIDs."""
        self.assertEqual(len(FIXTURE_USERS), 10)
        user_ids = set()
        user_emails = set()

        for user in FIXTURE_USERS:
            self.assertTrue(user.email.endswith("@lokal.dev"), f"{user.email} not in @lokal.dev")
            self.assertNotIn(user.id, user_ids, f"Duplicate user ID {user.id}")
            self.assertNotIn(user.email, user_emails, f"Duplicate user email {user.email}")
            user_ids.add(user.id)
            user_emails.add(user.email)

        # Check special roles
        curator = [u for u in FIXTURE_USERS if u.role == "curator"]
        self.assertEqual(len(curator), 1)
        self.assertEqual(curator[0].id, CURATOR_USER_ID)
        self.assertEqual(curator[0].app_metadata, {"role": "curator"})

        owner = [u for u in FIXTURE_USERS if u.role == "owner"]
        self.assertEqual(len(owner), 1)
        self.assertEqual(owner[0].id, OWNER_USER_ID)

    def test_claims_schema_and_integrity(self):
        """Assert claim fixture references valid shops and matches schema with claimant_role."""
        self.assertEqual(len(FIXTURE_CLAIMS), 1)
        claim = FIXTURE_CLAIMS[0]

        # Must have claimant_role (not business_role)
        self.assertEqual(claim.claimant_role, "Managing Partner")
        self.assertEqual(claim.user_id, OWNER_USER_ID)
        self.assertEqual(claim.curator_id, CURATOR_USER_ID)
        self.assertEqual(claim.status, "APPROVED")

        # Shop must be an approved shop
        target_shop = next(s for s in FIXTURE_SHOPS if s.id == claim.shop_id)
        self.assertEqual(target_shop.curation_status, "APPROVED")
        self.assertFalse(target_shop.is_real, "Owner claim must be on synthetic test cafe")

    def test_curation_audits_integrity(self):
        """Assert audit records exist for all shops with deterministic IDs."""
        self.assertEqual(len(FIXTURE_CURATION_AUDITS), 23)
        audit_ids = {a.id for a in FIXTURE_CURATION_AUDITS}
        self.assertEqual(len(audit_ids), 23)

        for audit in FIXTURE_CURATION_AUDITS:
            self.assertEqual(audit.change_source, "validation_seed")
            self.assertEqual(audit.changed_by, CURATOR_USER_ID)
            self.assertIsNotNone(audit.reason)

    def test_haversine_distance_tiers_and_discovery_assertions(self):
        """Assert exact discovery counts at 5km, 15km, and 25km radius from Manila reference coordinates."""
        ref_lat = 14.5995
        ref_lon = 120.9842

        # 5 km Radius Check: exactly 7 approved shops
        shops_within_5km = [
            s for s in FIXTURE_SHOPS
            if s.curation_status == "APPROVED"
            and haversine_distance_meters(ref_lat, ref_lon, s.latitude, s.longitude) <= 5000.0
        ]
        self.assertEqual(len(shops_within_5km), 7)

        # 15 km Radius Check: exactly 17 approved shops
        shops_within_15km = [
            s for s in FIXTURE_SHOPS
            if s.curation_status == "APPROVED"
            and haversine_distance_meters(ref_lat, ref_lon, s.latitude, s.longitude) <= 15000.0
        ]
        self.assertEqual(len(shops_within_15km), 17)

        # 25 km Radius Check: all 18 approved shops
        shops_within_25km = [
            s for s in FIXTURE_SHOPS
            if s.curation_status == "APPROVED"
            and haversine_distance_meters(ref_lat, ref_lon, s.latitude, s.longitude) <= 25000.0
        ]
        self.assertEqual(len(shops_within_25km), 18)

        # Negative Invariants: Excluded and Pending shops NEVER qualify as APPROVED at any radius
        for s in FIXTURE_SHOPS:
            if s.curation_status in ("EXCLUDED", "PENDING_REVIEW"):
                self.assertNotIn(s, shops_within_25km)


if __name__ == "__main__":
    unittest.main()
