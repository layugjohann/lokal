import os
import sys
import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from fastapi.testclient import TestClient
from app.main import app
from app.api.deps import get_authenticated_supabase, get_current_user, get_supabase
from app.core.config import settings
from app.schemas.auth import UserResponse
from app.schemas.curation import (
    CurationConfidence,
    CurationOverrideRequest,
    ShopEligibilityStatus,
)
from app.services.curation import (
    BrandNormalizer,
    CandidatePlace,
    CurationService,
    EligibilityClassifier,
    ExternalProviderError,
    GooglePlacesEvidenceProvider,
    LocationDeduplicator,
    ProviderSearchResult,
)


class DummyUser:
    def __init__(
        self,
        user_id="11111111-2222-3333-4444-555555555555",
        email="curator@lokal.ph",
        role="user",
        app_role=None,
    ):
        self.id = user_id
        self.email = email
        self.created_at = "2026-08-28T12:00:00Z"
        self.user_metadata = {"role": role}
        self.app_metadata = {"role": app_role if app_role is not None else role}



class MockQueryBuilder:
    def __init__(self, data=None):
        self._data = data
        self.last_inserted = None
        self.all_inserted = []
        self.last_updated = None
        self.last_eq = None
        self.eq_filters = []
        self.mock_execute = MagicMock()
        mock_resp = MagicMock()
        mock_resp.data = data
        self.mock_execute.return_value = mock_resp

    def insert(self, payload):
        self.last_inserted = payload
        self.all_inserted.append(payload)
        return self

    def upsert(self, payload):
        self.last_inserted = payload
        self.all_inserted.append(payload)
        return self

    def select(self, cols="*"):
        return self

    def update(self, payload):
        self.last_updated = payload
        return self

    def eq(self, col, val):
        self.last_eq = (col, val)
        self.eq_filters.append((col, val))
        return self

    def execute(self):
        return self.mock_execute()


class TestBrandNormalizer(unittest.TestCase):
    """Unit tests for brand name normalization and distinctiveness checks."""

    def test_extract_brand_strips_branch_delimiters(self):
        cases = [
            ("Yardstick Coffee - Legazpi Village", "Yardstick Coffee"),
            ("Starbucks (SM Megamall)", "Starbucks"),
            ("Blue Bottle Coffee @ Shibuya", "Blue Bottle Coffee"),
            ("Toby's Estate, Makati", "Toby's Estate"),
            ("Single Origin | BGC", "Single Origin"),
        ]
        for raw, expected in cases:
            res = BrandNormalizer.extract_brand(raw)
            self.assertEqual(res.normalized_brand, expected)
            self.assertTrue(res.is_distinctive)

    def test_extract_brand_detects_generic_names(self):
        generics = [
            "The Coffee Shop",
            "Cafe",
            "Espresso Bar",
            "Corner Cafe",
            "Daily Brew",
            "Coffee House",
        ]
        for name in generics:
            res = BrandNormalizer.extract_brand(name)
            self.assertFalse(res.is_distinctive, f"Expected '{name}' to be classified as non-distinctive")

    def test_extract_brand_detects_accented_generic_names(self):
        accented_generics = [
            "Café",
            "Le Café",
            "Café Bar",
            "Espresso Café",
        ]
        for name in accented_generics:
            res = BrandNormalizer.extract_brand(name)
            self.assertFalse(res.is_distinctive, f"Expected '{name}' to be classified as non-distinctive")

    def test_candidate_matching(self):
        brand = "Yardstick Coffee"
        self.assertTrue(BrandNormalizer.is_candidate_match("Yardstick Coffee Legazpi", brand))
        self.assertTrue(BrandNormalizer.is_candidate_match("Yardstick Coffee - Esteban", brand))
        self.assertFalse(BrandNormalizer.is_candidate_match("Starbucks Reserve", brand))
        self.assertFalse(BrandNormalizer.is_candidate_match("Local Cafe Near Yardstick", brand))


class TestLocationDeduplicator(unittest.TestCase):
    """Unit tests for Place ID and physical address deduplication."""

    def test_deduplicate_by_place_id(self):
        candidates = [
            CandidatePlace(place_id="ChIJ_1", display_name="Cafe A", formatted_address="123 Main St, Makati"),
            CandidatePlace(place_id="ChIJ_1", display_name="Cafe A Branch", formatted_address="123 Main St, Makati"),
            CandidatePlace(place_id="ChIJ_2", display_name="Cafe B", formatted_address="456 Other St, Makati"),
        ]
        deduped = LocationDeduplicator.deduplicate(candidates)
        self.assertEqual(len(deduped), 2)
        self.assertEqual({d.place_id for d in deduped}, {"ChIJ_1", "ChIJ_2"})

    def test_deduplicate_by_same_physical_address(self):
        # Two different Place IDs at the exact same physical building / suite
        candidates = [
            CandidatePlace(
                place_id="ChIJ_1",
                display_name="Kape Roastery",
                formatted_address="Unit 101, 106 Esteban St, Legazpi Village, Makati",
            ),
            CandidatePlace(
                place_id="ChIJ_2",
                display_name="Kape Cafe & Takeout",
                formatted_address="Unit 102, 106 Esteban St, Legazpi Village, Makati",
            ),
            CandidatePlace(
                place_id="ChIJ_3",
                display_name="Kape Branch 2",
                formatted_address="250 Salcedo St, Legazpi Village, Makati",
            ),
        ]
        deduped = LocationDeduplicator.deduplicate(candidates)
        # Esteban St addresses should collapse into 1 physical location
        self.assertEqual(len(deduped), 2)
        place_ids = {d.place_id for d in deduped}
        self.assertIn("ChIJ_1", place_ids)
        self.assertIn("ChIJ_3", place_ids)

    def test_deduplicate_preserves_street_numbers(self):
        candidates = [
            CandidatePlace(
                place_id="ChIJ_1",
                display_name="Cafe 1000",
                formatted_address="1000 Main St, Makati, 1229 Metro Manila",
            ),
            CandidatePlace(
                place_id="ChIJ_2",
                display_name="Cafe 2000",
                formatted_address="2000 Main St, Makati, 1229 Metro Manila",
            ),
        ]
        deduped = LocationDeduplicator.deduplicate(candidates)
        self.assertEqual(len(deduped), 2)



class TestEligibilityClassifier(unittest.IsolatedAsyncioTestCase):
    """Unit tests for asymmetric fail-closed eligibility classifier."""

    async def test_six_or_more_distinct_locations_classified_excluded(self):
        # 6 qualifying distinct locations
        places = [
            CandidatePlace(place_id=f"ChIJ_{i}", display_name=f"BigChain Branch {i}", formatted_address=f"Street {i}, Makati")
            for i in range(1, 7)
        ]
        mock_provider = AsyncMock()
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=places, next_page_token="tok_page2", has_more=True
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("BigChain Coffee - Main")

        self.assertEqual(decision.status, ShopEligibilityStatus.EXCLUDED)
        self.assertEqual(decision.confidence, CurationConfidence.HIGH)
        self.assertEqual(decision.location_count, 6)
        self.assertTrue(decision.is_short_circuit)

    async def test_duplicate_place_ids_do_not_inflate_location_count(self):
        # 5 physical locations duplicated across 8 items
        places = [
            CandidatePlace(place_id="ChIJ_1", display_name="LocalCraft A", formatted_address="10 St, Makati"),
            CandidatePlace(place_id="ChIJ_1", display_name="LocalCraft A", formatted_address="10 St, Makati"),
            CandidatePlace(place_id="ChIJ_2", display_name="LocalCraft B", formatted_address="20 St, Makati"),
            CandidatePlace(place_id="ChIJ_3", display_name="LocalCraft C", formatted_address="30 St, Makati"),
            CandidatePlace(place_id="ChIJ_4", display_name="LocalCraft D", formatted_address="40 St, Makati"),
            CandidatePlace(place_id="ChIJ_5", display_name="LocalCraft E", formatted_address="50 St, Makati"),
            CandidatePlace(place_id="ChIJ_5", display_name="LocalCraft E duplicate", formatted_address="50 St, Makati"),
        ]
        mock_provider = AsyncMock()
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=places, next_page_token=None, has_more=False
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("LocalCraft Coffee")

        self.assertEqual(decision.status, ShopEligibilityStatus.APPROVED)
        self.assertEqual(decision.confidence, CurationConfidence.HIGH)
        self.assertEqual(decision.location_count, 5)

    async def test_one_to_five_locations_terminal_classified_approved(self):
        places = [
            CandidatePlace(place_id="ChIJ_1", display_name="Yardstick Coffee", formatted_address="106 Esteban St, Makati, Metro Manila"),
            CandidatePlace(place_id="ChIJ_2", display_name="Yardstick Coffee MoA", formatted_address="Mall of Asia, Pasay, Metro Manila"),
        ]
        mock_provider = AsyncMock()
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=places, next_page_token=None, has_more=False
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("Yardstick Coffee")

        self.assertEqual(decision.status, ShopEligibilityStatus.APPROVED)
        self.assertEqual(decision.confidence, CurationConfidence.HIGH)
        self.assertEqual(decision.location_count, 2)

    async def test_one_to_five_locations_non_terminal_fails_closed_to_pending(self):
        places = [
            CandidatePlace(place_id="ChIJ_1", display_name="GrowingChain Coffee", formatted_address="10 St, Makati"),
            CandidatePlace(place_id="ChIJ_2", display_name="GrowingChain Coffee B", formatted_address="20 St, Taguig"),
        ]
        mock_provider = AsyncMock()
        # Non-terminal: has_more=True with next_page_token
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=places, next_page_token="tok_more_pages", has_more=True
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("GrowingChain Coffee")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.MEDIUM)
        self.assertEqual(decision.location_count, 2)
        self.assertIn("continuation token", decision.reason)

    async def test_regional_sprawl_fails_closed_to_pending(self):
        # 3 locations across 3 completely disparate island regions
        places = [
            CandidatePlace(place_id="ChIJ_1", display_name="SprawlCafe Manila", formatted_address="Makati, Metro Manila"),
            CandidatePlace(place_id="ChIJ_2", display_name="SprawlCafe Cebu", formatted_address="Cebu City, Cebu"),
            CandidatePlace(place_id="ChIJ_3", display_name="SprawlCafe Davao", formatted_address="Davao City, Davao"),
        ]
        mock_provider = AsyncMock()
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=places, next_page_token=None, has_more=False
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("SprawlCafe")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.MEDIUM)
        self.assertIn("multiple distant metropolitan regions", decision.reason)

    async def test_generic_name_fails_closed_to_pending_without_provider_call(self):
        mock_provider = AsyncMock()
        classifier = EligibilityClassifier(provider=mock_provider)

        decision = await classifier.classify("The Coffee Shop - Ground Floor")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.LOW)
        self.assertIsNone(decision.location_count)
        # External provider must not even be called for generic names
        mock_provider.search_locations.assert_not_called()

    async def test_provider_error_fails_closed_to_pending(self):
        mock_provider = AsyncMock()
        mock_provider.search_locations.side_effect = ExternalProviderError("Network timeout")

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("Artisan Beans")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.LOW)
        self.assertIsNone(decision.location_count)
        self.assertIn("unavailable", decision.reason)

    async def test_zero_results_fails_closed_to_pending(self):
        mock_provider = AsyncMock()
        mock_provider.search_locations.return_value = ProviderSearchResult(
            places=[], next_page_token=None, has_more=False
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("Hidden Gem Coffee")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.LOW)
        self.assertEqual(decision.location_count, 0)

    async def test_classifier_fails_closed_on_provider_malformed_continuation_token(self):
        mock_provider = AsyncMock()
        mock_provider.search_locations.side_effect = ExternalProviderError(
            "Google Places API returned an invalid response."
        )

        classifier = EligibilityClassifier(provider=mock_provider)
        decision = await classifier.classify("Independent Roasters")

        self.assertEqual(decision.status, ShopEligibilityStatus.PENDING_REVIEW)
        self.assertEqual(decision.confidence, CurationConfidence.LOW)
        self.assertIsNone(decision.location_count)
        self.assertIn("Evidence provider unavailable", decision.reason)


class TestCurationEndpoints(unittest.TestCase):
    """Integration tests for Curation API endpoints and authorization."""

    def setUp(self):
        self.mock_supabase = MagicMock()
        self.dummy_user = DummyUser(role="user")
        self.curator_user = DummyUser(user_id="22222222-3333-4444-5555-666666666666", email="curator@lokal.ph", role="curator")

        app.dependency_overrides[get_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_authenticated_supabase] = lambda: self.mock_supabase
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.dummy_user.id,
            email=self.dummy_user.email,
            created_at=self.dummy_user.created_at,
            user_metadata=self.dummy_user.user_metadata,
            app_metadata=self.dummy_user.app_metadata,
        )

        # Set curator email in settings for testing
        settings.CURATOR_EMAILS = ["curator@lokal.ph"]
        self.client = TestClient(app)
        self.shop_id = str(uuid4())

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_get_curation_success(self):
        record = {
            "shop_id": self.shop_id,
            "status": "APPROVED",
            "location_count": 2,
            "evidence_source": "google_places_text_search",
            "confidence": "HIGH",
            "is_manual_override": False,
            "curator_id": None,
            "curator_notes": "Verified 2 locations",
            "evaluated_at": "2026-09-18T00:00:00Z",
            "created_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:00:00Z",
        }
        builder = MockQueryBuilder(data=[record])
        self.mock_supabase.table.return_value = builder

        resp = self.client.get(f"/api/v1/shops/{self.shop_id}/curation")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "APPROVED")
        self.assertEqual(data["location_count"], 2)

    def test_override_forbidden_for_regular_user(self):
        # Current user is a regular user (role="user", email="user@lokal.ph")
        regular_user = DummyUser(email="regular@example.com", role="user")
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=regular_user.id,
            email=regular_user.email,
            created_at=regular_user.created_at,
            user_metadata=regular_user.user_metadata,
            app_metadata=regular_user.app_metadata,
        )

        payload = {"status": "APPROVED", "reason": "Curator override"}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Insufficient permissions", resp.json()["detail"])

    def test_override_forbidden_when_role_only_in_user_metadata(self):
        # Prevent privilege escalation via client-editable user_metadata (CWE-863)
        escalation_user = DummyUser(
            email="attacker@example.com",
            role="curator",
            app_role="user",
        )
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=escalation_user.id,
            email=escalation_user.email,
            created_at=escalation_user.created_at,
            user_metadata=escalation_user.user_metadata,
            app_metadata=escalation_user.app_metadata,
        )
        payload = {"status": "APPROVED", "reason": "Self grant"}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Insufficient permissions", resp.json()["detail"])

    def test_override_allowed_for_curator(self):
        # Override current user with curator
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.curator_user.id,
            email=self.curator_user.email,
            created_at=self.curator_user.created_at,
            user_metadata=self.curator_user.user_metadata,
            app_metadata=self.curator_user.app_metadata,
        )

        shop_data = [{"id": self.shop_id, "name": "Curated Cafe"}]
        curation_data = [{
            "shop_id": self.shop_id,
            "status": "APPROVED",
            "location_count": 1,
            "confidence": "HIGH",
            "is_manual_override": True,
            "curator_id": self.curator_user.id,
            "curator_notes": "Personally verified solo branch",
            "evaluated_at": "2026-09-18T00:00:00Z",
            "created_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:00:00Z",
        }]

        builder = MockQueryBuilder(data=curation_data)
        # Return shop_data on first table call, curation_data on subsequent
        self.mock_supabase.table.return_value = builder

        payload = {"status": "APPROVED", "reason": "Personally verified solo branch"}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "APPROVED")
        self.assertTrue(data["is_manual_override"])
        self.assertEqual(data["curator_notes"], "Personally verified solo branch")

    def test_override_validation_rejects_pending_review(self):
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.curator_user.id,
            email=self.curator_user.email,
            created_at=self.curator_user.created_at,
            user_metadata=self.curator_user.user_metadata,
        )
        payload = {"status": "PENDING_REVIEW", "reason": "Resetting"}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 422)

    def test_override_validation_rejects_empty_reason(self):
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.curator_user.id,
            email=self.curator_user.email,
            created_at=self.curator_user.created_at,
            user_metadata=self.curator_user.user_metadata,
        )
        payload = {"status": "APPROVED", "reason": "   "}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 422)

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_shop_success_approved(self, mock_search):
        mock_search.return_value = ProviderSearchResult(
            places=[
                CandidatePlace(place_id="ChIJ_1", display_name="Single Batch Roasters", formatted_address="10 Makati Ave, Makati"),
            ],
            next_page_token=None,
            has_more=False,
        )
        shop_data = [{"id": self.shop_id, "name": "Single Batch Roasters", "google_place_id": "ChIJ_1"}]
        builder = MockQueryBuilder(data=shop_data)
        self.mock_supabase.table.return_value = builder

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "APPROVED")
        self.assertEqual(data["location_count"], 1)
        self.assertEqual(data["confidence"], "HIGH")

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_growing_chain_transitions_approved_to_excluded(self, mock_search):
        # 6 locations returned for a brand previously approved
        places = [
            CandidatePlace(place_id=f"ChIJ_{i}", display_name=f"RapidGrow Coffee Branch {i}", formatted_address=f"St {i}, Makati")
            for i in range(1, 7)
        ]
        mock_search.return_value = ProviderSearchResult(
            places=places, next_page_token=None, has_more=False
        )
        shop_data = [{"id": self.shop_id, "name": "RapidGrow Coffee"}]
        builder = MockQueryBuilder(data=shop_data)
        self.mock_supabase.table.return_value = builder

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "EXCLUDED")
        self.assertEqual(data["location_count"], 6)
        self.assertEqual(data["confidence"], "HIGH")

    def test_evaluate_shop_locked_when_manual_override_active(self):
        shop_data = [{"id": self.shop_id, "name": "Protected Cafe"}]
        curation_data = [{
            "shop_id": self.shop_id,
            "status": "APPROVED",
            "location_count": 1,
            "is_manual_override": True,
            "evidence_source": "manual",
            "confidence": "HIGH",
            "evaluated_at": "2026-09-01T00:00:00Z",
        }]

        # Return shop on first call, curation on second
        call_count = [0]
        def table_router(table_name):
            builder = MockQueryBuilder()
            if table_name == "shops":
                builder._data = shop_data
                builder.mock_execute.return_value.data = shop_data
            elif table_name == "shop_curation":
                builder._data = curation_data
                builder.mock_execute.return_value.data = curation_data
            return builder

        self.mock_supabase.table.side_effect = table_router

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "APPROVED")
        self.assertTrue(data["is_manual_override"])
        self.assertIn("locked under manual curation override", data["message"])

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_shop_preserves_concurrent_manual_override(self, mock_search):
        # 1 candidate place found by provider
        mock_search.return_value = ProviderSearchResult(
            places=[
                CandidatePlace(place_id="ChIJ_1", display_name="Local Cafe", formatted_address="10 Makati Ave, Makati"),
            ],
            next_page_token=None,
            has_more=False,
        )
        shop_data = [{"id": self.shop_id, "name": "Local Cafe", "google_place_id": "ChIJ_1"}]
        # Initial curation check before classification returns non-override state
        initial_curation = [{
            "shop_id": self.shop_id,
            "status": "PENDING_REVIEW",
            "is_manual_override": False,
            "confidence": "LOW",
            "updated_at": "2026-09-18T00:00:00Z",
        }]
        # Manual override applied concurrently while search was running
        concurrent_override = [{
            "shop_id": self.shop_id,
            "status": "EXCLUDED",
            "location_count": 8,
            "is_manual_override": True,
            "confidence": "HIGH",
            "evidence_source": "manual",
            "curator_notes": "Manually excluded by curator",
            "evaluated_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:00:03Z",
        }]

        call_idx = {"curation_select": 0}

        def table_router(table_name):
            builder = MockQueryBuilder()
            if table_name == "shops":
                builder._data = shop_data
                builder.mock_execute.return_value.data = shop_data
            elif table_name == "shop_curation":
                def dynamic_execute():
                    resp = MagicMock()
                    if builder.last_updated is not None:
                        # Conditional update: if is_manual_override=False is checked,
                        # simulate that the row was updated to is_manual_override=True,
                        # so the update matches 0 rows!
                        resp.data = []
                        return resp
                    # Select query
                    if call_idx["curation_select"] == 0:
                        call_idx["curation_select"] += 1
                        resp.data = initial_curation
                    else:
                        resp.data = concurrent_override
                    return resp

                builder.mock_execute = dynamic_execute
            return builder

        self.mock_supabase.table.side_effect = table_router

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "EXCLUDED")
        self.assertTrue(data["is_manual_override"])
        self.assertEqual(data["confidence"], "HIGH")
        self.assertIn("Manual override applied during evaluation was preserved", data["message"])

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_shop_preserves_concurrent_automated_evaluation(self, mock_search):
        # Evaluation A finds 1 candidate place (would normally evaluate to APPROVED)
        mock_search.return_value = ProviderSearchResult(
            places=[
                CandidatePlace(place_id="ChIJ_1", display_name="Independent Cafe", formatted_address="10 Makati Ave, Makati"),
            ],
            next_page_token=None,
            has_more=False,
        )
        shop_data = [{"id": self.shop_id, "name": "Independent Cafe", "google_place_id": "ChIJ_1"}]
        # Initial curation state when Evaluation A starts
        initial_curation = [{
            "shop_id": self.shop_id,
            "status": "PENDING_REVIEW",
            "is_manual_override": False,
            "confidence": "LOW",
            "updated_at": "2026-09-18T00:00:00Z",
        }]
        # Evaluation B finished concurrently first, updating status to EXCLUDED and updated_at
        newer_concurrent_evaluation = [{
            "shop_id": self.shop_id,
            "status": "EXCLUDED",
            "location_count": 6,
            "is_manual_override": False,
            "confidence": "HIGH",
            "evidence_source": "google_places_text_search",
            "curator_notes": "Identified 6 qualifying locations",
            "evaluated_at": "2026-09-18T00:00:05Z",
            "updated_at": "2026-09-18T00:00:05Z",
        }]

        call_idx = {"curation_select": 0}

        def table_router(table_name):
            builder = MockQueryBuilder()
            if table_name == "shops":
                builder._data = shop_data
                builder.mock_execute.return_value.data = shop_data
            elif table_name == "shop_curation":
                def dynamic_execute():
                    resp = MagicMock()
                    if builder.last_updated is not None:
                        # Conditional update: since updated_at on the row is "2026-09-18T00:00:05Z"
                        # but Evaluation A sends eq("updated_at", "2026-09-18T00:00:00Z"),
                        # the OCC update matches 0 rows!
                        resp.data = []
                        return resp
                    # Select queries: first initial check, second re-query after OCC mismatch
                    if call_idx["curation_select"] == 0:
                        call_idx["curation_select"] += 1
                        resp.data = initial_curation
                    else:
                        resp.data = newer_concurrent_evaluation
                    return resp

                builder.mock_execute = dynamic_execute
            elif table_name == "shop_curation_audit":
                # Evaluation A's stale decision must NOT write an audit log
                builder.mock_execute.side_effect = AssertionError("Stale evaluation should not log audit record!")
            return builder

        self.mock_supabase.table.side_effect = table_router

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "EXCLUDED")
        self.assertFalse(data["is_manual_override"])
        self.assertEqual(data["confidence"], "HIGH")
        self.assertIn("A concurrent evaluation completed first. Latest persisted decision was preserved.", data["message"])

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_shop_reinitializes_if_curation_row_deleted(self, mock_search):
        mock_search.return_value = ProviderSearchResult(
            places=[
                CandidatePlace(place_id="ChIJ_1", display_name="Local Cafe", formatted_address="10 Makati Ave, Makati"),
            ],
            next_page_token=None,
            has_more=False,
        )
        shop_data = [{"id": self.shop_id, "name": "Local Cafe"}]
        initial_curation = [{
            "shop_id": self.shop_id,
            "status": "PENDING_REVIEW",
            "is_manual_override": False,
            "confidence": "LOW",
            "updated_at": "2026-09-18T00:00:00Z",
        }]

        call_idx = {"curation_select": 0}

        def table_router(table_name):
            builder = MockQueryBuilder()
            if table_name == "shops":
                builder._data = shop_data
                builder.mock_execute.return_value.data = shop_data
            elif table_name == "shop_curation":
                def dynamic_execute():
                    resp = MagicMock()
                    if builder.last_updated is not None:
                        # Row was deleted in-flight, update affects 0 rows
                        resp.data = []
                        return resp
                    if builder.last_inserted is not None:
                        # re-initialization insert
                        resp.data = [{
                            "shop_id": self.shop_id,
                            "status": "PENDING_REVIEW",
                            "confidence": "LOW",
                            "is_manual_override": False,
                        }]
                        return resp
                    if call_idx["curation_select"] == 0:
                        call_idx["curation_select"] += 1
                        resp.data = initial_curation
                    else:
                        # re-query after update failure finds no row (deleted)
                        resp.data = []
                    return resp

                builder.mock_execute = dynamic_execute
            return builder

        self.mock_supabase.table.side_effect = table_router

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["status"], "PENDING_REVIEW")
        self.assertIn("re-initialized", data["message"])

    def test_evaluate_shop_not_found(self):
        builder = MockQueryBuilder(data=[])
        self.mock_supabase.table.return_value = builder

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate")
        self.assertEqual(resp.status_code, 404)

    def test_evaluate_force_forbidden_for_regular_user(self):
        # Regular user cannot use force=True to bypass manual override locks (CWE-862)
        regular_user = DummyUser(email="regular@example.com", role="user", app_role="user")
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=regular_user.id,
            email=regular_user.email,
            created_at=regular_user.created_at,
            user_metadata=regular_user.user_metadata,
            app_metadata=regular_user.app_metadata,
        )
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate?force=true")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Insufficient permissions", resp.json()["detail"])

    @patch("app.services.curation.service.GooglePlacesEvidenceProvider.search_locations")
    def test_evaluate_force_allowed_for_curator(self, mock_search):
        mock_search.return_value = ProviderSearchResult(
            places=[CandidatePlace(place_id="ChIJ_1", display_name="Cafe", formatted_address="Makati")],
            next_page_token=None,
            has_more=False,
        )
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.curator_user.id,
            email=self.curator_user.email,
            created_at=self.curator_user.created_at,
            user_metadata=self.curator_user.user_metadata,
            app_metadata=self.curator_user.app_metadata,
        )
        shop_data = [{"id": self.shop_id, "name": "Cafe"}]
        builder = MockQueryBuilder(data=shop_data)
        self.mock_supabase.table.return_value = builder

        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/evaluate?force=true")
        self.assertEqual(resp.status_code, 200)

    def test_override_audit_failure_raises_500(self):
        # Audit logging failure must propagate 500 error instead of silently swallowing
        app.dependency_overrides[get_current_user] = lambda: UserResponse(
            id=self.curator_user.id,
            email=self.curator_user.email,
            created_at=self.curator_user.created_at,
            user_metadata=self.curator_user.user_metadata,
            app_metadata=self.curator_user.app_metadata,
        )
        shop_data = [{"id": self.shop_id, "name": "Curated Cafe"}]
        curation_data = [{
            "shop_id": self.shop_id,
            "status": "APPROVED",
            "location_count": 1,
            "confidence": "HIGH",
            "is_manual_override": True,
            "curator_id": self.curator_user.id,
            "curator_notes": "Verified",
            "evaluated_at": "2026-09-18T00:00:00Z",
            "created_at": "2026-09-18T00:00:00Z",
            "updated_at": "2026-09-18T00:00:00Z",
        }]

        def table_router(table_name):
            builder = MockQueryBuilder()
            if table_name == "shops":
                builder._data = shop_data
                builder.mock_execute.return_value.data = shop_data
            elif table_name == "shop_curation":
                builder._data = curation_data
                builder.mock_execute.return_value.data = curation_data
            elif table_name == "shop_curation_audit":
                builder.mock_execute.side_effect = Exception("Audit DB disk error")
            return builder

        self.mock_supabase.table.side_effect = table_router

        payload = {"status": "APPROVED", "reason": "Curator override"}
        resp = self.client.post(f"/api/v1/shops/{self.shop_id}/curation/override", json=payload)
        self.assertEqual(resp.status_code, 500)
        self.assertIn("recording curation audit trail", resp.json()["detail"])


class TestGooglePlacesEvidenceProvider(unittest.IsolatedAsyncioTestCase):
    """Unit tests for Google Places evidence provider network handling and validation."""

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_success(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "places": [
                {
                    "id": "ChIJ_test1",
                    "displayName": {"text": "Test Cafe"},
                    "formattedAddress": "123 Street, Makati",
                }
            ],
            "nextPageToken": "token123",
        }
        mock_post.return_value = mock_resp

        provider = GooglePlacesEvidenceProvider(api_key="test-key")
        result = await provider.search_locations("Test Cafe")

        self.assertEqual(len(result.places), 1)
        self.assertEqual(result.places[0].place_id, "ChIJ_test1")
        self.assertEqual(result.places[0].display_name, "Test Cafe")
        self.assertEqual(result.places[0].formatted_address, "123 Street, Makati")
        self.assertEqual(result.next_page_token, "token123")
        self.assertTrue(result.has_more)

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_malformed_json_non_dict(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = ["not", "a", "dict"]
        mock_post.return_value = mock_resp

        provider = GooglePlacesEvidenceProvider(api_key="test-key")
        with self.assertRaises(ExternalProviderError) as ctx:
            await provider.search_locations("Test Cafe")
        self.assertIn("invalid response", str(ctx.exception))

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_malformed_places_not_list(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"places": "invalid"}
        mock_post.return_value = mock_resp

        provider = GooglePlacesEvidenceProvider(api_key="test-key")
        with self.assertRaises(ExternalProviderError) as ctx:
            await provider.search_locations("Test Cafe")
        self.assertIn("invalid response", str(ctx.exception))

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_http_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        provider = GooglePlacesEvidenceProvider(api_key="test-key")
        with self.assertRaises(ExternalProviderError) as ctx:
            await provider.search_locations("Test Cafe")
        self.assertIn("HTTP 500", str(ctx.exception))

    @patch.object(settings, "GOOGLE_PLACES_API_KEY", "")
    async def test_search_locations_missing_api_key(self):
        provider = GooglePlacesEvidenceProvider(api_key="")
        with self.assertRaises(ExternalProviderError) as ctx:
            await provider.search_locations("Test Cafe")
        self.assertIn("not configured", str(ctx.exception))

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_malformed_next_page_token_non_string(self, mock_post):
        invalid_tokens = [123, True, {"token": "abc"}, ["tok1", "tok2"]]
        for invalid_token in invalid_tokens:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "places": [
                    {"id": "ChIJ_1", "displayName": {"text": "Cafe"}, "formattedAddress": "Makati"}
                ],
                "nextPageToken": invalid_token,
            }
            mock_post.return_value = mock_resp

            provider = GooglePlacesEvidenceProvider(api_key="test-key")
            with self.assertRaises(ExternalProviderError) as ctx:
                await provider.search_locations("Test Cafe")
            self.assertIn("invalid response", str(ctx.exception))

    @patch("httpx.AsyncClient.post")
    async def test_search_locations_malformed_next_page_token_empty_string(self, mock_post):
        empty_tokens = ["", "   "]
        for empty_token in empty_tokens:
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            mock_resp.json.return_value = {
                "places": [
                    {"id": "ChIJ_1", "displayName": {"text": "Cafe"}, "formattedAddress": "Makati"}
                ],
                "nextPageToken": empty_token,
            }
            mock_post.return_value = mock_resp

            provider = GooglePlacesEvidenceProvider(api_key="test-key")
            with self.assertRaises(ExternalProviderError) as ctx:
                await provider.search_locations("Test Cafe")
            self.assertIn("invalid response", str(ctx.exception))



