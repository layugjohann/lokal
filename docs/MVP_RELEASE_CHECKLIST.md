# LOKAL MVP End-to-End Validation & Release-Readiness Checklist (Issue #55)

**Validation Date:** 2026-10-20  
**Branch:** `feature/55-mvp-e2e-validation-checklist`  
**Target Environment:** Local Docker Supabase Stack (`http://127.0.0.1:54321`, `project_id = "lokal"`) + Local FastAPI Server (`http://127.0.0.1:8000`) + Expo Mobile Client (`mobile/`)  
**Remote Database Mutated:** No (`thustdjwwtkhlhbnuvin.supabase.co` untouched)

---

## 1. Executive Summary & Release Recommendation

| Category | Status | Summary |
| :--- | :--- | :--- |
| **Local Supabase Stack & Schema** | **PASS** | 12 local Docker containers healthy (`postgres`, `kong`, `gotrue`, `postgrest`, `realtime`, `storage`, `studio`, etc.); all 10 SQL migrations and 7 RPCs verified. |
| **Validation Dataset Integrity (Issue #49)** | **PASS** | `23/23` shops, `23/23` curation records, `23/23` curation audits, `23/23` first-party reviews, `8/8` favorites, `1/1` claim, and `10/10` `@lokal.dev` Auth accounts seeded, idempotently re-verified (`0` conflicts), and dry-run clean verified. |
| **Priority 0 User Journeys (Core MVP)** | **PASS** | Auth lifecycle, protected route enforcement, nearby discovery (`5 km`, `15 km`, `25 km`), search/filters/sorting, shop detail, review provenance, synthetic Place ID resilience, first-party review CRUD, AI summary/recommendation thresholds (`< 3` reviews), and fail-closed curation boundaries (`404`/`400`) verified against the live local stack. |
| **Priority 1 User Journeys (Secondary MVP)** | **PASS** | Favorites & per-account RLS isolation, Community Feed chronological pagination (`23` items across `3` pages), Personalized "For You" recommendations (history vs. empty-history fallback), and Owner Claim/Dashboard/Profile update & restoration verified end-to-end. |
| **Automated Test & Build Gates** | **PASS** | Backend (`443/443` pass), Mobile (`228/228` pass), pgTAP DB (`109/109` pass across 4 suites), TypeScript (`tsc --noEmit` `0` errors), iOS & Android Expo bundle exports (`npx expo export` `0` errors). |
| **Live External Providers (Google Places & Gemini)** | **BLOCKED** | `GOOGLE_PLACES_API_KEY` and `GEMINI_API_KEY` are not configured in `.env`. Synthetic-fixture and mocked-provider grounding/fallback tests pass; live outbound Google Places and Gemini generation checks remain **BLOCKED** pending production/staging API keys. |
| **Interactive Simulator UI Walkthrough** | **PENDING PO ACCEPTANCE** | Live mobile TypeScript service clients (`mobile/src/services/*.ts`) and iOS/Android Hermes bundles were verified against the running FastAPI + local Supabase stack. Interactive visual simulator sign-off is reserved for Product Owner acceptance. |

### Overall Release-Readiness Recommendation: **CONDITIONAL GO (Ready for Product Owner Simulator Acceptance; Live API Keys Required Before External Production Launch)**

- **For Local / Controlled MVP Demo & Product Owner Simulator Review:** **GO** — All database migrations, RLS policies, RPCs, backend endpoints, mobile controllers/services, and iOS/Android Expo bundles are verified and healthy against the populated 23-shop validation dataset.
- **Before Public / External Production Cutover:** **HOLD until `GOOGLE_PLACES_API_KEY` and `GEMINI_API_KEY` are provisioned** in the target deployment environment and the two live-provider checks (Section 5) are executed.

---

## 2. Environment & Dataset Readiness Verification

### 2.1 Local Supabase Stack & Schema Verification

| Check | Command / Evidence | Result |
| :--- | :--- | :--- |
| Local Supabase project configuration | `supabase/config.toml` initialized (`project_id = "lokal"`, API port `54321`, DB port `54322`, Postgres `17`) | **PASS** |
| Local Docker service health | `supabase_db_lokal`, `supabase_kong_lokal`, `supabase_auth_lokal`, `supabase_rest_lokal`, `supabase_realtime_lokal`, `supabase_storage_lokal`, `supabase_studio_lokal` all `Up (healthy)` | **PASS** |
| Applied SQL migrations | All `10` migrations (`20260811000000_initial_schema` through `20261007000000_community_feed`) present in `supabase_migrations.schema_migrations` | **PASS** |
| Required PostgreSQL RPCs | All `7` RPCs verified in `public` schema: `approve_shop_claim`, `create_user_favorite`, `create_user_review`, `get_community_feed`, `get_nearby_shops`, `get_shop_review_aggregates`, `update_user_review` | **PASS** |
| Loopback HTTP URL guard (`backend/app/core/supabase.py`) | `validate_supabase_url()` permits `http://` strictly for `127.0.0.1`, `localhost`, and `::1` when `ENVIRONMENT=development`; rejects remote HTTP, non-development HTTP, lookalike hostnames, and embedded credentials across all client factories | **PASS** |
| Backend -> Local Supabase reachability | `verify_supabase_connection()` returned `{'status': 'connected', 'url': 'http://127.0.0.1:54321', 'status_code': 200}` | **PASS** |

### 2.2 Validation Dataset Seeding & Idempotency (Issue #49 Tooling)

Executed against `http://127.0.0.1:54321` via `python -m backend.scripts.seed_validation_data`:

1. `seed` (initial population) -> `0` errors
2. `verify` (post-seed verification) -> `ALL FIXTURE RECORDS AND AUTH IDENTITIES VERIFIED SUCCESSFULLY`
3. `seed` + `verify` (second pass idempotency test) -> `0` conflicts, all existing accounts and records preserved untouched
4. `clean --dry-run` -> previewed exact fixture counts with `Zero records were modified`
5. `clean` -> `supabase test db` -> `seed` -> `verify` -> verified full teardown and clean re-seeding without drift

| Managed Entity | Expected Count | Actual Verified Count | Breakdown / Provenance Notes | Result |
| :--- | :---: | :---: | :--- | :---: |
| `shops` | `23` | `23` | `12` real `APPROVED` cafés (`rating = NULL`), `6` synthetic `[Test]` `APPROVED` cafés, `3` real `EXCLUDED` chains (`>= 6` branches), `2` synthetic `[Test Curation]` `PENDING_REVIEW` cafés | **PASS** |
| `shop_curation` | `23` | `23` | `18` `APPROVED`, `3` `EXCLUDED`, `2` `PENDING_REVIEW` | **PASS** |
| `shop_curation_audit` | `23` | `23` | Deterministic audit trail (`00000000-0000-4000-f000-000000000001` .. `0023`) | **PASS** |
| `reviews` | `23` | `23` | `100%` first-party (`source = 'lokal'`), distributed strictly across synthetic `[Test]` shops (`8` on Escolta Lab, `3` on Intramuros Guild, `1` on Binondo Cold Brew, `0` on Malate Hub, `5` on Metro Mixed, `6` on BGC Artisan); **`0` fabricated reviews on real cafés** | **PASS** |
| `favorites` | `8` | `8` | Deterministic favorites across test scouts (`00000000-0000-4000-e000-000000000001` .. `0008`) | **PASS** |
| `shop_claims` | `1` | `1` | `APPROVED` claim (`00000000-0000-4000-d000-000000000001`) by `owner.roberto@lokal.dev` on `[Test] Escolta Specialty Coffee Lab` | **PASS** |
| `auth.users` (`@lokal.dev`) | `10` | `10` | `8` reviewer scouts (`scout.juan` .. `scout.hannah`), `1` verified shop owner (`owner.roberto`), `1` curator (`curator.admin`) | **PASS** |

---

## 3. Priority 0 End-to-End Validation Matrix (Core MVP Flows)

| ID | Flow / Scenario | Validation Method & Evidence | Status |
| :--- | :--- | :--- | :---: |
| **P0-1** | **Unauthenticated Route Protection** | `GET /api/v1/shops/nearby` and `GET /api/v1/auth/me` without Bearer token return `401 Unauthorized` (`test_p0_auth_lifecycle_and_protected_routes`). | **PASS** |
| **P0-2** | **User Sign-In, `/auth/me`, & Invalid Credentials** | `POST /api/v1/auth/login` with `scout.juan@lokal.dev` returns `200 OK` + session JWT; `GET /api/v1/auth/me` returns deterministic user ID `00000000-0000-4000-b000-000000000001` and `full_name`; invalid password returns `401`. | **PASS** |
| **P0-3** | **Scoped Sign-Out** | `POST /api/v1/auth/logout` revokes only the caller's token via GoTrue without global sign-out side effects (`200 OK`). | **PASS** |
| **P0-4** | **Nearby Discovery Across Radius Tiers (`5 km`, `15 km`, `25 km`)** | `GET /api/v1/shops/nearby` from Makati CBD (`14.5535, 121.0195`) returns monotonically increasing results up to `18` `APPROVED` shops at `25,000m`, ordered by ascending `distance_meters`. Verified both via FastAPI `TestClient` and live Mobile TS `fetchNearbyShops()`. | **PASS** |
| **P0-5** | **Search, Minimum Ratings & Sort Modes** | `GET /api/v1/shops/nearby` with `query=Escolta&min_rating=4.5&min_lokal_rating=4.5&sort_by=lokal_rating` returns `[Test] Escolta Specialty Coffee Lab` (`lokal_reviews_count = 8`, `lokal_rating = 4.63`). | **PASS** |
| **P0-6** | **Shop Detail & Real Café Provenance Protection** | `GET /api/v1/shops/00000000-0000-4000-a000-000000000001` (`The Den Coffee & Contemporary Culture`) returns `200 OK` with `rating = None` and `0` rows in `public.reviews`. Unclaimed status confirmed via `GET /api/v1/shops/{id}/claim` (`null`). | **PASS** |
| **P0-7** | **Unified Reviews & Synthetic Place ID Resilience** | `GET /api/v1/shops/00000000-0000-4000-a000-000000000013/reviews` (`google_place_id = "test-place-escolta-lab"`) returns `200 OK` with `8` first-party LOKAL reviews (`lokal_reviews_count = 8`, `lokal_average_rating = 4.62`, `total_reviews_count = 0`, `attributions = []`), including `is_edited = true` on review `0005`. | **PASS** |
| **P0-8** | **First-Party Review Create / Duplicate / Edit / Delete Lifecycle** | On `[Test] Malate Pour-over Hub` (`0016`), `POST /reviews` creates review (`201`), duplicate `POST` returns `409 Conflict`, `PATCH /reviews/mine` updates rating/text and sets `is_edited = true` (`200`), and `DELETE /reviews/mine` removes the review (`200`), restoring the `0`-review baseline. | **PASS** |
| **P0-9** | **AI Review Summary & "Must Try" Minimum Thresholds (`< 3` Reviews)** | Below-threshold shop (`[Test] Binondo Cold Brew Studio`, `1` review) and zero-review shop (`[Test] Malate Pour-over Hub`, `0` reviews) return `200 OK` with `status = "insufficient_reviews"` and accurate `review_count_analyzed` (`1` and `0`) on both `/reviews/summary` and `/reviews/recommendations`. | **PASS** |
| **P0-10** | **AI Summary & "Must Try" 5-Point Grounding & Safe Unconfigured Fallback** | With `GEMINI_API_KEY` unconfigured locally, eligible shops (`>= 3` reviews) fail closed with `503 Service Unavailable` (never `500`). Five-point grounding (`validate_and_convert_recommendations`), negation detection, cache invalidation, and schema validation verified across `backend/tests/test_review_summary.py` and `backend/tests/test_review_recommendations.py`. | **PASS** |
| **P0-11** | **Fail-Closed Curation Boundary (`EXCLUDED` & `PENDING_REVIEW`)** | Standard users requesting `Yardstick Coffee` (`0019`, `EXCLUDED`, `9` branches) or `[Test Curation] Generic Manila Coffee Bar` (`0022`, `PENDING_REVIEW`) receive `404` on `/shops/{id}`, `/reviews`, `/reviews/summary`, `/reviews/recommendations`, and `/favorite`, and `400`/`404` on review/claim mutations. | **PASS** |

---

## 4. Priority 1 End-to-End Validation Matrix (Secondary MVP Flows)

| ID | Flow / Scenario | Validation Method & Evidence | Status |
| :--- | :--- | :--- | :---: |
| **P1-1** | **Favorites Lifecycle & Cross-Account Isolation** | `GET /api/v1/favorites` returns `3` favorites for `scout.juan@lokal.dev` (`0013`, `0014`, `0015`) and `1` favorite for `scout.maria@lokal.dev` (`0013`). Adding a favorite on `0016` for Juan (`201`) sets `is_favorite = true` for Juan while remaining `false` for Maria; `DELETE` (`200`) restores baseline. | **PASS** |
| **P1-2** | **Community Feed Ordering & Offset Pagination** | `GET /api/v1/community/feed?limit=10&offset=0..20` pages through all `23` seeded first-party reviews across `3` pages (`10 + 10 + 3`) with `0` duplicates, newest-first ordering, no unapproved shop leakage, and `has_more = false` on page 3. | **PASS** |
| **P1-3** | **Personalized "For You" Recommendations & Cold-Start Fallback** | `GET /api/v1/shops/recommendations/personalized` returns `status = "personalized"` with `5` ranked `APPROVED` shop recommendations and grounded explanations for `scout.juan@lokal.dev` (has review + favorite history), and `status = "insufficient_data"` (`recommendations = []`) for `curator.admin@lokal.dev` (`0` reviews, `0` favorites). | **PASS** |
| **P1-4** | **Owner Claim, Dashboard Access Control & Profile Update** | `GET /api/v1/owner/shops/00000000-0000-4000-a000-000000000013/dashboard` returns `403 Forbidden` for non-owner `scout.juan@lokal.dev` and `200 OK` (`claim.status = "APPROVED"`, `lokal_reviews_count = 8`, `5` recent reviews) for verified owner `owner.roberto@lokal.dev`. `PATCH /api/v1/owner/shops/{id}` rejects protected fields (`rating`) with `422` and updates `address` (`200 OK`), followed by baseline restoration. | **PASS** |

---

## 5. Live External Provider Checks (Blocked / Skipped Matrix)

Per Product Owner Decision #2, mocked provider tests are strictly separated from live external API checks:

| Check | Required Credential | Status | Reason & Behavior Verified |
| :--- | :--- | :---: | :--- |
| **Live Google Places Reviews Fetch** (`GET /api/v1/shops/{real_shop_id}/reviews` on Category A real cafés with `ChIJ*` Place IDs) | `GOOGLE_PLACES_API_KEY` | **BLOCKED** | `GOOGLE_PLACES_API_KEY` is not set in local `.env`. Without the key, genuine `ChIJ*` Place IDs raise `ExternalProviderError` -> `502 Bad Gateway` as designed, while synthetic `test-place-*` fixtures return `200 OK` with first-party LOKAL reviews. |
| **Live Gemini AI Review Summary & "Must Try" Generation** (`GET /api/v1/shops/{id}/reviews/summary` and `/reviews/recommendations` on shops with `>= 3` reviews) | `GEMINI_API_KEY` | **BLOCKED** | `GEMINI_API_KEY` is not set in local `.env`. Without the key, shops with `< 3` reviews return `200 OK` (`insufficient_reviews`) and shops with `>= 3` reviews return `503 Service Unavailable`. |
| **Live Gemini Personalized "For You" Explanations** (`GET /api/v1/shops/recommendations/personalized`) | `GEMINI_API_KEY` | **SKIPPED (Graceful Fallback Active)** | Without `GEMINI_API_KEY`, `PersonalizedRecommendationService` automatically falls back to deterministic evidence-based explanations (`status = "personalized"`, `5` recommendations returned with `200 OK`). |

---

## 6. Defects Discovered & Resolved During Validation

1. **Local Supabase Stack Initialization & Loopback HTTP Validation (`backend/app/core/supabase.py`):**
   - **Finding:** Only the standalone `supabase_db_lokal` Postgres container was running initially (without `supabase/config.toml`, Kong, GoTrue, or PostgREST), and `backend/app/core/supabase.py` rejected all `http://` URLs even for local development loopback (`http://127.0.0.1:54321`).
   - **Resolution:** Initialized `supabase/config.toml` (`project_id = "lokal"`), started the full 12-container local Supabase stack, and added `validate_supabase_url()` in [`backend/app/core/supabase.py`](file:///Users/antonlayug/Desktop/portfolio%20projects/lokal/backend/app/core/supabase.py) permitting `http://` strictly for `127.0.0.1`, `localhost`, and `::1` when `ENVIRONMENT == "development"`. Added 5 unit tests in [`backend/tests/test_auth.py`](file:///Users/antonlayug/Desktop/portfolio%20projects/lokal/backend/tests/test_auth.py) covering all client factory functions.
2. **Synthetic Google Place ID Outbound Request Short-Circuit (`backend/app/services/reviews/google_places.py`):**
   - **Finding:** Category B synthetic `[Test]` shops use `google_place_id` values prefixed with `test-place-`. Calling `GET /api/v1/shops/{id}/reviews` on a synthetic `[Test]` shop previously attempted an outbound Google Places request (or failed with `502` when `GOOGLE_PLACES_API_KEY` was unset), preventing first-party LOKAL reviews from loading on synthetic validation fixtures.
   - **Resolution:** Added a narrow guard in [`GooglePlacesReviewProvider.fetch_reviews`](file:///Users/antonlayug/Desktop/portfolio%20projects/lokal/backend/app/services/reviews/google_places.py) so IDs prefixed with `test-place-` immediately return `[], None, None, None` without making outbound Google Places requests, while preserving `ExternalProviderError` (`502`) semantics for genuine Google Place IDs. Added regression coverage in [`backend/tests/test_reviews.py`](file:///Users/antonlayug/Desktop/portfolio%20projects/lokal/backend/tests/test_reviews.py).
3. **pgTAP Suite Precondition (`supabase/tests/02..04`):**
   - **Finding:** `supabase/tests/02_advanced_search_and_filters.sql`, `03_shop_claims.sql`, and `04_community_feed.sql` insert transaction-scoped fixtures and assert exact aggregate counts assuming `public.shops`, `public.reviews`, and `public.shop_claims` are empty prior to the test run.
   - **Operational Note:** Run `python -m backend.scripts.seed_validation_data clean` before executing `supabase test db`, then re-run `python -m backend.scripts.seed_validation_data seed && python -m backend.scripts.seed_validation_data verify`.

---

## 7. Automated Test, Type Check & Build Verification Results

| Verification Suite | Command | Result | Details |
| :--- | :--- | :---: | :--- |
| **Backend Unit & E2E Suite** | `./backend/.venv/bin/python -m unittest discover -s backend/tests -v` | **PASS** | `443` tests run in `7.99s` (`0` failures, `0` errors, `0` skipped) |
| **Live Local Supabase E2E Suite** | `./backend/.venv/bin/python -m unittest backend/tests/test_mvp_e2e_validation.py -v` | **PASS** | `9` end-to-end P0/P1 user journeys passed against `http://127.0.0.1:54321` |
| **Database pgTAP Suites** | `supabase test db` | **PASS** | `4` test files (`01`–`04`), `109 / 109` assertions passed |
| **Mobile Unit & Controller Suite** | `npm test --prefix mobile` | **PASS** | `228 / 228` tests passed (`0` failures) |
| **Mobile TypeScript Check** | `./mobile/node_modules/.bin/tsc --noEmit --project mobile/tsconfig.json` | **PASS** | `0` errors |
| **Expo iOS Bundle Export** | `npx expo export --platform ios` | **PASS** | Bundled `2674` modules (`4.1 MB` Hermes bytecode `.hbc`) |
| **Expo Android Bundle Export** | `npx expo export --platform android` | **PASS** | Bundled `2672` modules (`4.1 MB` Hermes bytecode `.hbc`) |
| **Live Mobile TS Services -> FastAPI -> Local Supabase** | Live `uvicorn` (`127.0.0.1:8000`) + Node ESM execution of `mobile/src/services/*.ts` | **PASS** | Verified `nearbyCount=18`, `escoltaLokalReviews=8`, `summaryLowStatus=insufficient_reviews`, `recsLowStatus=insufficient_reviews`, `feedItemsCount=10`, `personalizedStatus=personalized`, `favoritesCount=3`, `ownerDashboardClaimStatus=APPROVED` |
| **Post-Validation Dataset Integrity** | `python -m backend.scripts.seed_validation_data verify` | **PASS** | `23/23` shops, `23/23` curation, `23/23` audits, `23/23` reviews, `8/8` favorites, `1/1` claim, `10/10` Auth users (`0` diffs) |

---

## 8. Product Owner Simulator Acceptance Guide

To perform final interactive simulator acceptance against the populated local stack:

1. **Ensure Local Supabase is Running:**
   ```bash
   supabase status
   ```
   *(API URL: `http://127.0.0.1:54321`)*
2. **Start FastAPI Backend Against Local Supabase:**
   Configure `.env` (or export in shell) with `ENVIRONMENT=development`, `SUPABASE_URL=http://127.0.0.1:54321`, and the local `ANON_KEY` and `SERVICE_ROLE_KEY` from `supabase status -o env`, then run:
   ```bash
   ./backend/.venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 --app-dir backend
   ```
3. **Start Expo Mobile App:**
   With `EXPO_PUBLIC_API_URL=http://127.0.0.1:8000` and `EXPO_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321`:
   ```bash
   npm start --prefix mobile
   ```
4. **Recommended Test Personas (Password configured via `TEST_USER_PASSWORD` during seeding):**
   - **Primary Reviewer / Taste History Persona:** `scout.juan@lokal.dev` (4 reviews, 3 favorites, active "For You" recommendations)
   - **Secondary Reviewer (Isolation Check):** `scout.maria@lokal.dev` (3 reviews, 1 favorite)
   - **Verified Shop Owner Persona:** `owner.roberto@lokal.dev` (verified owner of `[Test] Escolta Specialty Coffee Lab`)
   - **Cold-Start / Curator Persona:** `curator.admin@lokal.dev` (0 reviews, 0 favorites, curator role)
