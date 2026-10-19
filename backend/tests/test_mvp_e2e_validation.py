"""End-to-end MVP validation test suite against the local Docker Supabase stack (Issue #55).

Executes Priority 0 and Priority 1 release-readiness user journeys against the
populated local Supabase environment (`http://127.0.0.1:54321`) while strictly
preserving the Issue #49 baseline dataset.
"""

import json
import os
import subprocess
import sys
import unittest
from urllib.parse import urlparse

# Ensure backend directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import httpx
from fastapi.testclient import TestClient

import app.core.supabase as supabase_module
from app.core.config import settings
from app.main import app


LOCAL_LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

# Fixture UUIDs from backend/app/fixtures/validation_dataset.py
SHOP_THE_DEN_REAL = "00000000-0000-4000-a000-000000000001"
SHOP_THE_CURATOR_REAL = "00000000-0000-4000-a000-000000000004"
SHOP_ESCOLTA_LAB_TEST = "00000000-0000-4000-a000-000000000013"      # 8 reviews, claimed by owner.roberto
SHOP_INTRAMUROS_GUILD_TEST = "00000000-0000-4000-a000-000000000014" # 3 reviews (exact AI threshold)
SHOP_BINONDO_COLDBREW_TEST = "00000000-0000-4000-a000-000000000015" # 1 review (< 3 threshold)
SHOP_MALATE_HUB_TEST = "00000000-0000-4000-a000-000000000016"       # 0 reviews
SHOP_METRO_MIXED_TEST = "00000000-0000-4000-a000-000000000017"      # 5 reviews (mixed sentiment)
SHOP_BGC_ARTISAN_TEST = "00000000-0000-4000-a000-000000000018"      # 6 reviews

SHOP_YARDSTICK_EXCLUDED = "00000000-0000-4000-a000-000000000019"    # EXCLUDED (9 branches)
SHOP_TOBYS_EXCLUDED = "00000000-0000-4000-a000-000000000020"        # EXCLUDED (18 branches)
SHOP_STARBUCKS_EXCLUDED = "00000000-0000-4000-a000-000000000021"    # EXCLUDED (400 branches)
SHOP_PENDING_GENERIC_TEST = "00000000-0000-4000-a000-000000000022"  # PENDING_REVIEW
SHOP_PENDING_CORNER_TEST = "00000000-0000-4000-a000-000000000023"   # PENDING_REVIEW

REVIEW_ESCOLTA_1 = "00000000-0000-4000-c000-000000000001"
REVIEW_ESCOLTA_5_EDITED = "00000000-0000-4000-c000-000000000005"


def _resolve_local_supabase_config() -> dict[str, str] | None:
    """Resolve local Docker Supabase credentials safely without touching remote hosts."""
    env_url = (os.environ.get("SUPABASE_URL") or "").strip()
    env_anon = (os.environ.get("SUPABASE_ANON_KEY") or "").strip()
    env_sr = (os.environ.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip()

    if env_url and urlparse(env_url).hostname in LOCAL_LOOPBACK_HOSTS and env_anon and env_sr:
        return {
            "API_URL": env_url,
            "ANON_KEY": env_anon,
            "SERVICE_ROLE_KEY": env_sr,
        }

    try:
        raw = subprocess.check_output(
            ["supabase", "status", "-o", "json"],
            stderr=subprocess.DEVNULL,
            text=True,
            timeout=15,
        )
        data = json.loads(raw)

        api_url = (data.get("API_URL") or "").strip()
        if urlparse(api_url).hostname in LOCAL_LOOPBACK_HOSTS:
            return {
                "API_URL": api_url,
                "ANON_KEY": data["ANON_KEY"],
                "SERVICE_ROLE_KEY": data["SERVICE_ROLE_KEY"],
            }
    except Exception:
        return None
    return None


class TestMvpLocalSupabaseE2E(unittest.TestCase):
    """Live local-stack E2E tests covering Priority 0 and Priority 1 MVP journeys."""

    @classmethod
    def setUpClass(cls):
        cfg = _resolve_local_supabase_config()
        if not cfg:
            raise unittest.SkipTest(
                "Local Docker Supabase stack (127.0.0.1:54321) is not active; skipping live E2E suite."
            )

        parsed_host = (urlparse(cfg["API_URL"]).hostname or "").lower()
        if parsed_host not in LOCAL_LOOPBACK_HOSTS:
            raise RuntimeError(
                f"Refusing to run E2E validation suite against non-loopback host '{parsed_host}'."
            )

        cls.test_user_password = (
            settings.TEST_USER_PASSWORD or os.environ.get("TEST_USER_PASSWORD") or ""
        ).strip()
        if not cls.test_user_password:
            raise unittest.SkipTest(
                "TEST_USER_PASSWORD is not configured in environment; skipping live E2E suite."
            )

        # Verify local REST endpoint is reachable and seeded before mutating settings
        try:
            with httpx.Client(timeout=3.0) as http_client:
                resp = http_client.get(
                    f"{cfg['API_URL'].rstrip('/')}/rest/v1/shops?select=id&limit=1",
                    headers={
                        "apikey": cfg["ANON_KEY"],
                        "Authorization": f"Bearer {cfg['ANON_KEY']}",
                    },
                )
                if resp.status_code != 200 or not resp.json():
                    raise unittest.SkipTest(
                        "Local Supabase database is not seeded with validation fixtures."
                    )
        except unittest.SkipTest:
            raise
        except Exception as exc:
            raise unittest.SkipTest(f"Local Supabase REST API unreachable: {exc}") from exc

        # Save original settings and cached clients
        cls._orig_env = settings.ENVIRONMENT
        cls._orig_url = settings.SUPABASE_URL
        cls._orig_anon = settings.SUPABASE_ANON_KEY
        cls._orig_sr = settings.SUPABASE_SERVICE_ROLE_KEY
        cls._orig_google_key = settings.GOOGLE_PLACES_API_KEY
        cls._orig_gemini_key = settings.GEMINI_API_KEY
        cls._orig_client = supabase_module._supabase_client
        cls._orig_sr_client = supabase_module._service_role_supabase_client

        settings.ENVIRONMENT = "development"
        settings.SUPABASE_URL = cfg["API_URL"]
        settings.SUPABASE_ANON_KEY = cfg["ANON_KEY"]
        settings.SUPABASE_SERVICE_ROLE_KEY = cfg["SERVICE_ROLE_KEY"]
        supabase_module._supabase_client = None
        supabase_module._service_role_supabase_client = None

        cls.client = TestClient(app)
        cls.sr_supabase = supabase_module.get_service_role_supabase_client()

        # Authenticate key validation personas once for read/write journeys
        cls.juan_token = cls._login("scout.juan@lokal.dev")
        cls.maria_token = cls._login("scout.maria@lokal.dev")
        cls.curator_token = cls._login("curator.admin@lokal.dev")
        cls.owner_token = cls._login("owner.roberto@lokal.dev")

    @classmethod
    def tearDownClass(cls):
        settings.ENVIRONMENT = cls._orig_env
        settings.SUPABASE_URL = cls._orig_url
        settings.SUPABASE_ANON_KEY = cls._orig_anon
        settings.SUPABASE_SERVICE_ROLE_KEY = cls._orig_sr
        settings.GOOGLE_PLACES_API_KEY = cls._orig_google_key
        settings.GEMINI_API_KEY = cls._orig_gemini_key
        supabase_module._supabase_client = cls._orig_client
        supabase_module._service_role_supabase_client = cls._orig_sr_client

    @classmethod
    def _login(cls, email: str) -> str:
        resp = cls.client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": cls.test_user_password},
        )
        if resp.status_code != 200:
            raise AssertionError(f"Login failed for {email}: {resp.status_code} {resp.text}")
        return resp.json()["session"]["access_token"]

    @staticmethod
    def _headers(token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"}

    # ------------------------------------------------------------------
    # Priority 0: Auth, Protected Routes, Session Restoration & Logout
    # ------------------------------------------------------------------
    def test_p0_auth_lifecycle_and_protected_routes(self):
        # 1. Protected endpoints reject unauthenticated requests
        unauth_nearby = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5535&longitude=121.0195"
        )
        self.assertEqual(unauth_nearby.status_code, 401)

        unauth_me = self.client.get("/api/v1/auth/me")
        self.assertEqual(unauth_me.status_code, 401)

        # 2. Invalid credentials return 401
        bad_login = self.client.post(
            "/api/v1/auth/login",
            json={"email": "scout.juan@lokal.dev", "password": "WrongPassword123!"},
        )
        self.assertEqual(bad_login.status_code, 401)

        # 3. Authenticated /me returns deterministic Juan Dela Cruz profile
        me_resp = self.client.get("/api/v1/auth/me", headers=self._headers(self.juan_token))
        self.assertEqual(me_resp.status_code, 200)
        me_data = me_resp.json()
        self.assertEqual(me_data["id"], "00000000-0000-4000-b000-000000000001")
        self.assertEqual(me_data["email"], "scout.juan@lokal.dev")
        self.assertEqual(me_data["user_metadata"]["full_name"], "Juan Dela Cruz (LOKAL Scout)")

        # 4. Separate login + logout cycle revokes only that session
        temp_token = self._login("scout.hannah@lokal.dev")
        logout_resp = self.client.post("/api/v1/auth/logout", headers=self._headers(temp_token))
        self.assertEqual(logout_resp.status_code, 200)
        self.assertEqual(logout_resp.json()["message"], "Successfully signed out.")

    # ------------------------------------------------------------------
    # Priority 0: Nearby Discovery, Radius Tiers, Search, Filters & Sort
    # ------------------------------------------------------------------
    def test_p0_nearby_discovery_curation_and_filters(self):
        headers = self._headers(self.juan_token)

        # 5 km, 15 km, and 25 km tiers from Makati CBD
        resp_5k = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5535&longitude=121.0195&radius=5000",
            headers=headers,
        )
        resp_15k = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5535&longitude=121.0195&radius=15000",
            headers=headers,
        )
        resp_25k = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5535&longitude=121.0195&radius=25000",
            headers=headers,
        )
        self.assertEqual(resp_5k.status_code, 200)
        self.assertEqual(resp_15k.status_code, 200)
        self.assertEqual(resp_25k.status_code, 200)

        shops_5k = resp_5k.json()
        shops_15k = resp_15k.json()
        shops_25k = resp_25k.json()

        self.assertGreater(len(shops_5k), 0)
        self.assertLessEqual(len(shops_5k), len(shops_15k))
        self.assertEqual(len(shops_25k), 18)  # Exactly 18 APPROVED shops in the 23-shop dataset

        returned_ids = {s["id"] for s in shops_25k}
        for unapproved_id in (
            SHOP_YARDSTICK_EXCLUDED,
            SHOP_TOBYS_EXCLUDED,
            SHOP_STARBUCKS_EXCLUDED,
            SHOP_PENDING_GENERIC_TEST,
            SHOP_PENDING_CORNER_TEST,
        ):
            self.assertNotIn(unapproved_id, returned_ids)

        # Distance sort is strictly ascending
        distances = [s["distance_meters"] for s in shops_25k]
        self.assertEqual(distances, sorted(distances))

        # Check first-party review aggregates on [Test] Escolta Specialty Coffee Lab (8 reviews)
        escolta = next(s for s in shops_25k if s["id"] == SHOP_ESCOLTA_LAB_TEST)
        self.assertEqual(escolta["lokal_reviews_count"], 8)
        self.assertAlmostEqual(escolta["lokal_rating"], 4.63, places=2)

        # Search query + min_rating + min_lokal_rating + sort_by=lokal_rating
        filtered = self.client.get(
            "/api/v1/shops/nearby?latitude=14.5535&longitude=121.0195&radius=25000"
            "&query=Escolta&min_rating=4.5&min_lokal_rating=4.5&sort_by=lokal_rating",
            headers=headers,
        )
        self.assertEqual(filtered.status_code, 200)
        filtered_data = filtered.json()
        self.assertEqual(len(filtered_data), 1)
        self.assertEqual(filtered_data[0]["id"], SHOP_ESCOLTA_LAB_TEST)

    # ------------------------------------------------------------------
    # Priority 0: Shop Detail, Review Provenance & Synthetic Place IDs
    # ------------------------------------------------------------------
    def test_p0_shop_detail_and_review_provenance(self):
        headers = self._headers(self.juan_token)

        # 1. Real café detail & provenance check (0 fabricated first-party reviews)
        real_detail = self.client.get(
            f"/api/v1/shops/{SHOP_THE_DEN_REAL}",
            headers=headers,
        )
        self.assertEqual(real_detail.status_code, 200)
        self.assertEqual(real_detail.json()["name"], "The Den Coffee & Contemporary Culture")
        self.assertIsNone(real_detail.json()["rating"])

        claim_status = self.client.get(
            f"/api/v1/shops/{SHOP_THE_DEN_REAL}/claim",
            headers=headers,
        )
        self.assertEqual(claim_status.status_code, 200)
        self.assertIsNone(claim_status.json())

        real_db_reviews = (
            self.sr_supabase.table("reviews")
            .select("id")
            .eq("shop_id", SHOP_THE_DEN_REAL)
            .execute()
        )
        self.assertEqual(real_db_reviews.data, [])

        # 2. Synthetic [Test] shop with test-place-* Place ID succeeds without Google API key
        synth_reviews_resp = self.client.get(
            f"/api/v1/shops/{SHOP_ESCOLTA_LAB_TEST}/reviews",
            headers=headers,
        )
        self.assertEqual(synth_reviews_resp.status_code, 200)
        synth_reviews = synth_reviews_resp.json()
        self.assertEqual(synth_reviews["lokal_reviews_count"], 8)
        self.assertAlmostEqual(synth_reviews["lokal_average_rating"], 4.62, places=2)
        self.assertEqual(synth_reviews["total_reviews_count"], 0)
        self.assertEqual(synth_reviews["attributions"], [])
        self.assertEqual(len(synth_reviews["reviews"]), 8)
        for rev in synth_reviews["reviews"]:
            self.assertEqual(rev["source"], "lokal")
            self.assertTrue(rev["id"].startswith("lokal:"))

        edited_rev = next(
            r for r in synth_reviews["reviews"] if r["id"] == f"lokal:{REVIEW_ESCOLTA_5_EDITED}"
        )
        self.assertTrue(edited_rev["is_edited"])

        # 3. Review CRUD lifecycle on zero-review synthetic shop (restoring baseline in finally)
        try:
            create_resp = self.client.post(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/reviews",
                headers=headers,
                json={
                    "rating": 5,
                    "content": "E2E validation test review: smooth pour-over and friendly baristas.",
                },
            )
            self.assertEqual(create_resp.status_code, 201)
            created = create_resp.json()
            self.assertEqual(created["source"], "lokal")
            self.assertEqual(created["author"]["display_name"], "Juan Dela Cruz (LOKAL Scout)")
            self.assertFalse(created["is_edited"])

            # Duplicate review rejected with 409
            dup_resp = self.client.post(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/reviews",
                headers=headers,
                json={"rating": 4, "content": "Duplicate review attempt."},
            )
            self.assertEqual(dup_resp.status_code, 409)

            # Edit review via PATCH /reviews/mine
            patch_resp = self.client.patch(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/reviews/mine",
                headers=headers,
                json={"rating": 4, "content": "Updated E2E validation review text."},
            )
            self.assertEqual(patch_resp.status_code, 200)
            patched = patch_resp.json()
            self.assertEqual(patched["rating"], 4.0)
            self.assertEqual(patched["text"], "Updated E2E validation review text.")
            self.assertTrue(patched["is_edited"])
        finally:
            del_resp = self.client.delete(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/reviews/mine",
                headers=headers,
            )
            self.assertIn(del_resp.status_code, (200, 404))

    # ------------------------------------------------------------------
    # Priority 0: AI Summary & Must Try Thresholds and Safe Fallbacks
    # ------------------------------------------------------------------
    def test_p0_ai_summary_and_recommendations_grounding(self):
        headers = self._headers(self.juan_token)

        # 1. Below-threshold shop (1 review < 3 minimum)
        low_sum = self.client.get(
            f"/api/v1/shops/{SHOP_BINONDO_COLDBREW_TEST}/reviews/summary",
            headers=headers,
        )
        self.assertEqual(low_sum.status_code, 200)
        self.assertEqual(low_sum.json()["status"], "insufficient_reviews")
        self.assertEqual(low_sum.json()["review_count_analyzed"], 1)

        low_rec = self.client.get(
            f"/api/v1/shops/{SHOP_BINONDO_COLDBREW_TEST}/reviews/recommendations",
            headers=headers,
        )
        self.assertEqual(low_rec.status_code, 200)
        self.assertEqual(low_rec.json()["status"], "insufficient_reviews")
        self.assertEqual(low_rec.json()["review_count_analyzed"], 1)

        # 2. Zero-review shop (0 reviews < 3 minimum)
        zero_sum = self.client.get(
            f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/reviews/summary",
            headers=headers,
        )
        self.assertEqual(zero_sum.status_code, 200)
        self.assertEqual(zero_sum.json()["status"], "insufficient_reviews")
        self.assertEqual(zero_sum.json()["review_count_analyzed"], 0)

        # 3. Exact-threshold (3 reviews) and rich-review (8 reviews) shops:
        #    return 200 when GEMINI_API_KEY is configured, or 503 when unconfigured (never 500)
        for shop_id, expected_count in (
            (SHOP_INTRAMUROS_GUILD_TEST, 3),
            (SHOP_ESCOLTA_LAB_TEST, 8),
        ):
            with self.subTest(shop_id=shop_id):
                elig_sum = self.client.get(
                    f"/api/v1/shops/{shop_id}/reviews/summary",
                    headers=headers,
                )
                if settings.GEMINI_API_KEY:
                    self.assertIn(elig_sum.status_code, (200, 502))
                    if elig_sum.status_code == 200:
                        self.assertEqual(elig_sum.json()["status"], "available")
                        self.assertEqual(elig_sum.json()["review_count_analyzed"], expected_count)
                else:
                    self.assertEqual(elig_sum.status_code, 503)

                elig_rec = self.client.get(
                    f"/api/v1/shops/{shop_id}/reviews/recommendations",
                    headers=headers,
                )
                if settings.GEMINI_API_KEY:
                    self.assertIn(elig_rec.status_code, (200, 502))
                    if elig_rec.status_code == 200:
                        self.assertEqual(elig_rec.json()["status"], "available")
                        self.assertEqual(elig_rec.json()["review_count_analyzed"], expected_count)
                else:
                    self.assertEqual(elig_rec.status_code, 503)

    # ------------------------------------------------------------------
    # Priority 0: Curation Enforcement Boundary
    # ------------------------------------------------------------------
    def test_p0_curation_enforcement_boundary(self):
        headers = self._headers(self.juan_token)

        for unapproved_shop_id in (SHOP_YARDSTICK_EXCLUDED, SHOP_PENDING_GENERIC_TEST):
            with self.subTest(shop_id=unapproved_shop_id):
                self.assertEqual(
                    self.client.get(f"/api/v1/shops/{unapproved_shop_id}", headers=headers).status_code,
                    404,
                )
                self.assertEqual(
                    self.client.get(
                        f"/api/v1/shops/{unapproved_shop_id}/reviews", headers=headers
                    ).status_code,
                    404,
                )
                self.assertEqual(
                    self.client.get(
                        f"/api/v1/shops/{unapproved_shop_id}/reviews/summary", headers=headers
                    ).status_code,
                    404,
                )
                self.assertEqual(
                    self.client.get(
                        f"/api/v1/shops/{unapproved_shop_id}/reviews/recommendations",
                        headers=headers,
                    ).status_code,
                    404,
                )
                self.assertIn(
                    self.client.post(
                        f"/api/v1/shops/{unapproved_shop_id}/reviews",
                        headers=headers,
                        json={"rating": 5, "content": "Should be rejected by curation guard."},
                    ).status_code,
                    (400, 404),
                )
                self.assertEqual(
                    self.client.post(
                        f"/api/v1/shops/{unapproved_shop_id}/favorite", headers=headers
                    ).status_code,
                    404,
                )
                self.assertEqual(
                    self.client.post(
                        f"/api/v1/shops/{unapproved_shop_id}/claim",
                        headers=headers,
                        json={
                            "claimant_name": "Juan Dela Cruz",
                            "claimant_role": "Owner",
                            "business_proof": "DTI Proof",
                        },
                    ).status_code,
                    400,
                )

    # ------------------------------------------------------------------
    # Priority 1: Favorites & Account Isolation
    # ------------------------------------------------------------------
    def test_p1_favorites_and_account_isolation(self):
        juan_headers = self._headers(self.juan_token)
        maria_headers = self._headers(self.maria_token)

        juan_favs = self.client.get("/api/v1/favorites", headers=juan_headers)
        self.assertEqual(juan_favs.status_code, 200)
        juan_fav_ids = {s["id"] for s in juan_favs.json()}
        self.assertEqual(
            juan_fav_ids,
            {SHOP_ESCOLTA_LAB_TEST, SHOP_INTRAMUROS_GUILD_TEST, SHOP_BINONDO_COLDBREW_TEST},
        )

        maria_favs = self.client.get("/api/v1/favorites", headers=maria_headers)
        self.assertEqual(maria_favs.status_code, 200)
        maria_fav_ids = {s["id"] for s in maria_favs.json()}
        self.assertEqual(maria_fav_ids, {SHOP_ESCOLTA_LAB_TEST})

        try:
            add_resp = self.client.post(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/favorite",
                headers=juan_headers,
            )
            self.assertEqual(add_resp.status_code, 201)

            juan_status = self.client.get(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/favorite",
                headers=juan_headers,
            )
            self.assertTrue(juan_status.json()["is_favorite"])

            maria_status = self.client.get(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/favorite",
                headers=maria_headers,
            )
            self.assertFalse(maria_status.json()["is_favorite"])
        finally:
            del_resp = self.client.delete(
                f"/api/v1/shops/{SHOP_MALATE_HUB_TEST}/favorite",
                headers=juan_headers,
            )
            self.assertIn(del_resp.status_code, (200, 404))

    # ------------------------------------------------------------------
    # Priority 1: Community Feed & Offset Pagination
    # ------------------------------------------------------------------
    def test_p1_community_feed_and_cursor_pagination(self):
        headers = self._headers(self.juan_token)
        seen_ids: list[str] = []
        offset = 0
        limit = 10
        pages = 0

        while True:
            resp = self.client.get(
                f"/api/v1/community/feed?limit={limit}&offset={offset}",
                headers=headers,
            )
            self.assertEqual(resp.status_code, 200)
            body = resp.json()
            pages += 1

            for item in body["items"]:
                self.assertNotIn(item["id"], seen_ids)
                seen_ids.append(item["id"])
                self.assertNotIn(
                    item["shop_id"],
                    {
                        SHOP_YARDSTICK_EXCLUDED,
                        SHOP_TOBYS_EXCLUDED,
                        SHOP_STARBUCKS_EXCLUDED,
                        SHOP_PENDING_GENERIC_TEST,
                        SHOP_PENDING_CORNER_TEST,
                    },
                )

            if not body["has_more"]:
                break
            offset += limit
            self.assertLessEqual(pages, 5)

        self.assertEqual(len(seen_ids), 23)
        self.assertEqual(pages, 3)

    # ------------------------------------------------------------------
    # Priority 1: Personalized "For You" Recommendations
    # ------------------------------------------------------------------
    def test_p1_personalized_recommendations(self):
        # 1. User with taste history (Juan Dela Cruz: 4 reviews + 3 favorites)
        juan_resp = self.client.get(
            "/api/v1/shops/recommendations/personalized?latitude=14.5535&longitude=121.0195&radius=25000&limit=5",
            headers=self._headers(self.juan_token),
        )
        self.assertEqual(juan_resp.status_code, 200)
        juan_data = juan_resp.json()
        self.assertEqual(juan_data["status"], "personalized")
        self.assertGreater(len(juan_data["recommendations"]), 0)
        self.assertLessEqual(len(juan_data["recommendations"]), 5)

        for rec in juan_data["recommendations"]:
            self.assertTrue(rec["explanation"])
            self.assertNotIn(
                rec["shop"]["id"],
                {
                    SHOP_YARDSTICK_EXCLUDED,
                    SHOP_TOBYS_EXCLUDED,
                    SHOP_STARBUCKS_EXCLUDED,
                    SHOP_PENDING_GENERIC_TEST,
                    SHOP_PENDING_CORNER_TEST,
                },
            )

        # 2. User with zero reviews and zero favorites (Curator Admin)
        empty_resp = self.client.get(
            "/api/v1/shops/recommendations/personalized?latitude=14.5535&longitude=121.0195&radius=25000&limit=5",
            headers=self._headers(self.curator_token),
        )
        self.assertEqual(empty_resp.status_code, 200)
        empty_data = empty_resp.json()
        self.assertEqual(empty_data["status"], "insufficient_data")
        self.assertEqual(empty_data["recommendations"], [])

    # ------------------------------------------------------------------
    # Priority 1: Owner Claim, Dashboard, & Profile Editing
    # ------------------------------------------------------------------
    def test_p1_owner_claim_dashboard_and_mutations_restored(self):
        juan_headers = self._headers(self.juan_token)
        owner_headers = self._headers(self.owner_token)

        # 1. Non-owner is denied access to owner dashboard (403)
        non_owner_dash = self.client.get(
            f"/api/v1/owner/shops/{SHOP_ESCOLTA_LAB_TEST}/dashboard",
            headers=juan_headers,
        )
        self.assertEqual(non_owner_dash.status_code, 403)

        # 2. Verified owner Roberto accesses dashboard (200)
        owner_dash = self.client.get(
            f"/api/v1/owner/shops/{SHOP_ESCOLTA_LAB_TEST}/dashboard",
            headers=owner_headers,
        )
        self.assertEqual(owner_dash.status_code, 200)
        dash_data = owner_dash.json()
        self.assertEqual(dash_data["shop"]["id"], SHOP_ESCOLTA_LAB_TEST)
        self.assertEqual(dash_data["claim"]["status"], "APPROVED")
        self.assertEqual(dash_data["lokal_reviews_count"], 8)
        self.assertEqual(len(dash_data["recent_reviews"]), 5)


        orig_address = dash_data["shop"]["address"]
        orig_updated_at = dash_data["shop"]["updated_at"]

        # 3. Protected fields are rejected at schema boundary (422)
        forbidden_patch = self.client.patch(
            f"/api/v1/owner/shops/{SHOP_ESCOLTA_LAB_TEST}",
            headers=owner_headers,
            json={"rating": 5.0},
        )
        self.assertEqual(forbidden_patch.status_code, 422)

        # 4. Owner updates permitted address field, then restores exact baseline record
        try:
            profile_resp = self.client.patch(
                f"/api/v1/owner/shops/{SHOP_ESCOLTA_LAB_TEST}",
                headers=owner_headers,
                json={"address": "Unit 201B, Escolta Test Plaza, Binondo, Manila"},
            )
            self.assertEqual(profile_resp.status_code, 200)
            self.assertEqual(
                profile_resp.json()["address"],
                "Unit 201B, Escolta Test Plaza, Binondo, Manila",
            )
        finally:
            self.sr_supabase.table("shops").update(
                {"address": orig_address, "updated_at": orig_updated_at}
            ).eq("id", SHOP_ESCOLTA_LAB_TEST).execute()


if __name__ == "__main__":
    unittest.main()
