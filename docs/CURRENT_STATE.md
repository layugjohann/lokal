# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, independent business eligibility and curation, external review data layer, first-party LOKAL user reviews, mobile user authentication with secure session management, AI-generated review summaries, AI-generated "Must Try" recommendations, and favorite coffee shops are established.

The project is now building application-level features that expand LOKAL's core user experience and community discovery capabilities.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed milestone, **Harden Supabase Public-Schema Access and RLS Policies (GitHub Issue #37)**, hardened database security across all six public tables (`shops`, `menu_items`, `shop_curation`, `shop_curation_audit`, `reviews`, `favorites`), eliminated the Supabase Security Advisor `rls_disabled_in_public` finding, and established a strict least-privilege authorization model.

Direct PostgREST mutation access on `shops` has been revoked for all client roles (`anon`, `authenticated`, `public`). The intended security boundary is enforced: ordinary users can only read approved coffee shops, while shop mutations (`POST /api/v1/shops`, `PATCH /api/v1/shops/{id}`, `DELETE /api/v1/shops/{id}`) and curation evaluation/inspection (`GET /api/v1/shops/{id}/curation`, `POST /api/v1/shops/{id}/curation/evaluate`) must proceed through the trusted FastAPI gateway using curator authorization (`require_curator`) and a dedicated fail-closed service-role database client (`get_service_role_supabase`). Column-level grants restrict public direct Data API visibility on `shop_curation` strictly to `(shop_id, status)` for approved shops, preventing unauthorized exposure of internal curation metadata, notes, and confidence scores.

Database security and RLS policies are verified through an executable 55-assertion pgTAP test suite (`supabase/tests/01_rls_and_permissions.sql`) alongside the full 297-test backend regression suite and 109-test mobile regression suite.

The engineering workflow remains formalized under the **AI-Assisted Engineering Workflow**.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #37 — Harden Supabase Public-Schema Access and RLS Policies

**Status:** ✅ Completed

### Completed Work

* **Database Security, Least-Privilege Grants & Row Level Security (RLS)**:
  * Implemented migration `supabase/migrations/20261001000000_harden_public_schema_and_rls.sql`.
  * Enabled and enforced Row Level Security across all six exposed public tables: `shops`, `menu_items`, `shop_curation`, `shop_curation_audit`, `reviews`, and `favorites`, resolving the Supabase Security Advisor `rls_disabled_in_public` finding.
  * Least-privilege grant and revocation matrix:
    * `shops`: Revoked default `ALL` privileges from `anon`, `authenticated`, and `public`. Granted `SELECT` to `anon` and `authenticated`. Revoked direct client `INSERT`, `UPDATE`, and `DELETE` grants from all client roles; granted full `ALL` access to `service_role`.
    * `shop_curation`: Revoked direct table-level `SELECT` from `anon`, `authenticated`, and `public`. Granted column-level `SELECT (shop_id, status)` strictly to `anon` and `authenticated`. Internal curation metadata (`curator_notes`, `evidence_source`, `confidence`, `curator_id`, `location_count`) is restricted from direct public consumption; full curation records are accessible only to curators via FastAPI using `service_role`.
    * `menu_items`: Revoked all access from `anon`, `authenticated`, and `public`. Restricted strictly to `service_role` (no direct PostgREST Data API exposure).
    * `shop_curation_audit`: Revoked all access from `anon` and `public`. Granted `SELECT` to `authenticated` with an RLS policy restricting visibility strictly to callers with JWT `role IN ('curator', 'admin')`. Mutations restricted to `service_role`.
    * `reviews` and `favorites`: Preserved strict row-level ownership isolation (`auth.uid() = user_id`) on `SELECT` and `DELETE`; direct client `INSERT` and `UPDATE` remain revoked, requiring writes to flow through security-definer RPCs or FastAPI.
  * Scoped RLS Policies:
    * `shops`: Ordinary read policy allows `anon` and `authenticated` callers to read approved shops (`status = 'APPROVED'`). Privileged read policy allows users with `role IN ('curator', 'admin')` to read all shops. Direct client mutation policies are dropped.
    * `shop_curation`: Ordinary read policy restricts `anon` and `authenticated` access to rows where `status = 'APPROVED'`. Curator/admin read policy allows reading curation status for non-approved shops. Full access granted to `service_role`.
    * `menu_items` and `shop_curation_audit`: Dedicated `service_role` policies with audit read access for authenticated curators/admins.
* **Dedicated Service-Role Backend Client & Fail-Closed Dependency**:
  * Implemented `get_service_role_supabase_client()` in `backend/app/core/supabase.py`:
    * Requires `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.
    * Never falls back to `SUPABASE_ANON_KEY`.
  * Implemented `get_service_role_supabase()` dependency in `backend/app/api/deps.py`:
    * Yields the authenticated service-role client.
    * Fails closed with `HTTP 503 Service Unavailable` if `SUPABASE_SERVICE_ROLE_KEY` is not configured, preventing unauthenticated fallback or silent degradation.
    * Service-role credentials remain strictly server-side and are never exposed to mobile or client code.
* **FastAPI Shop & Curation Authorization**:
  * Protected shop mutations in `backend/app/api/v1/endpoints/shops.py`:
    * Added `require_curator` and `get_service_role_supabase()` dependencies to `create_shop` (`POST /api/v1/shops`), `update_shop` (`PATCH /api/v1/shops/{id}`), and `delete_shop` (`DELETE /api/v1/shops/{id}`).
    * Ordinary authenticated users receive `403 Forbidden` on mutation attempts.
  * Protected curation endpoints in `backend/app/api/v1/endpoints/curation.py`:
    * Added `require_curator` and `get_service_role_supabase()` to `get_shop_curation` (`GET /api/v1/shops/{id}/curation`) and `evaluate_shop_curation` (`POST /api/v1/shops/{id}/curation/evaluate`).
    * Ordinary authenticated users receive `403 Forbidden` when attempting to inspect full curation metadata or trigger curation evaluations.
    * Simplified redundant `force=True` curator check once the entire evaluation endpoint is curator-protected.
* **Database pgTAP Authorization Test Suite**:
  * Implemented and expanded `supabase/tests/01_rls_and_permissions.sql` containing **55 planned assertions** (`plan(55)`):
    * Metadata verification (Tests 1–22): Confirms RLS enabled on all 6 tables, table privileges, and column privileges for `anon` and `authenticated`.
    * `anon` executable tests (Tests 23–32): Proves `anon` can read approved shops and cannot read pending shops; confirms `INSERT`/`UPDATE`/`DELETE` on `shops` throws `42501`; confirms column-restricted `SELECT` on `shop_curation`; confirms `SELECT` on `menu_items` and `shop_curation_audit` throws `42501`.
    * Ordinary `authenticated` executable tests (Tests 33–48): Proves ordinary users can read approved shops and cannot read pending shops; confirms direct `INSERT`/`UPDATE`/`DELETE` on `shops` throws `42501`; confirms `shop_curation_audit` returns 0 rows via RLS; confirms cross-user ownership isolation on reviews and favorites (cannot read or delete other users' records; can delete own record).
    * Curator `authenticated` executable tests (Tests 49–55): Proves curators can read approved and pending shops; can read pending curation status; can read curation audit logs; confirms direct PostgREST shop mutations remain denied (must use FastAPI gateway).
* **Automated Verification**:
  * Database pgTAP test suite: **55 / 55 assertions passed** (100%).
  * Backend regression suite: **297 passing tests** (`PYTHONPATH=backend ./backend/.venv/bin/python -m unittest discover -s backend/tests -t backend`), adding 6 focused authorization and service-role failure tests in `test_shops.py` and `test_curation.py`.
  * Mobile regression suite: **109 passing tests** (`npm test --prefix mobile`).
  * Mobile TypeScript compiler: **0 errors** (`./mobile/node_modules/.bin/tsc --noEmit --project mobile/tsconfig.json`).
* **Pull Request**:
  * Pull Request #38 reviewed by CodeRabbit, actionable findings resolved iteratively (revoked direct authenticated shop mutation grants and policies, expanded executable pgTAP coverage), approved, and merged into `main` by the Product Owner (merge commit `a65d9d32`).

---

# Project Progress

| Feature / Milestone                                          | Status      |
| ------------------------------------------------------------ | ----------- |
| Engineering Foundation                                       | ✅ Complete |
| Issue #1 — Initialize Mobile Application                     | ✅ Complete |
| Issue #3 — Initialize FastAPI Backend                        | ✅ Complete |
| Issue #5 — Initialize Supabase Integration                   | ✅ Complete |
| Issue #7 — Database Schema                                   | ✅ Complete |
| Issue #9 — User Authentication                               | ✅ Complete |
| Issue #11 — Maps & Location Integration                      | ✅ Complete |
| Issue #13 — Coffee Shop CRUD API                             | ✅ Complete |
| Issue #15 — Coffee Shop Discovery & Search                   | ✅ Complete |
| Issue #19 — External Review Data Layer                        | ✅ Complete |
| Issue #22 — Independent Business Eligibility & Shop Curation | ✅ Complete |
| Issue #24 — LOKAL User Reviews                               | ✅ Complete |
| Issue #29 — Mobile User Authentication & Session Management  | ✅ Complete |
| AI-Assisted Engineering Workflow                             | ✅ Complete |
| Issue #31 — AI-Generated Review Summaries                    | ✅ Complete |
| Issue #33 — AI-Generated "Must Try" Recommendations          | ✅ Complete |
| Issue #35 — Favorite Coffee Shops                            | ✅ Complete |
| Issue #37 — Harden Supabase Public Schema & RLS              | ✅ Complete |
| User Favorites List / Profile Discovery                      | ⏳ Planned  |

---

# Current Mobile Capabilities

The React Native (Expo) mobile application currently provides:

* **Authentication & Session Lifecycle Management**:
  * User registration and login screens (`RegisterView`, `LoginView`) with input validation, password matching, inline error presentation, and loading states.
  * Hardware-backed credential persistence via `expo-secure-store` with fail-fast security preventing silent in-memory downgrades in native or production runtimes.
  * Automatic session restoration on application launch with backend profile validation against `/api/v1/auth/me`.
  * Distinct error handling for invalid sessions (automatic token purging on `401 Unauthorized`) versus transient network/server failures (credential preservation with recovery UI).
  * Dedicated restoration error recovery UI offering both **Retry** and **Sign Out** actions.
  * Fail-safe sign-out ensuring local credentials are unconditionally deleted regardless of backend network availability.
  * Monotonic operation generation guards (`operationGenerationRef`) protecting the authentication provider against asynchronous race conditions across concurrent logins, retries, and logouts.
  * Automatic Bearer token propagation across nearby coffee shop searches, review operations, and AI summary requests.
* **Favorite Coffee Shops**:
  * Interactive favorite heart button integrated directly into the `ShopDetailCard` header.
  * Discrete tri-state favorite modeling (`boolean | null`) separating confirmed favorited (`true`), confirmed non-favorited (`false`), and unconfirmed/loading/error (`null`).
  * Control disablement during unconfirmed, loading, or mutating states (`opacity: 0.5`) with accessible labeling (`Favorite status unavailable`).
  * Immediate optimistic UI toggle with automatic rollback on network or server error.
  * In-banner retry action enabling immediate recovery upon status load failure without requiring the user to leave or re-select the shop.
  * Unauthenticated guest handling providing an inline sign-in prompt without triggering network mutation requests.
  * Monotonic request and mutation sequence counters (`currentFavoriteRequestId`, `currentFavoriteMutationId`) preventing race conditions and stale responses across rapid shop selection changes.
* **AI-Generated Review Summaries**:
  * Non-blocking AI review summary card within `ShopDetailCard`.
  * Asynchronous background fetching initiated after shop selection, leaving the rest of the detail card responsive.
  * Concise overall synthesis paragraph summarizing customer sentiment and opinions.
  * Visual highlight chips distinguishing positive highlights and areas to note (negative themes).
  * Graceful insufficient reviews state informing the user when fewer than 3 usable reviews exist.
  * Error state presentation with localized retry action.
  * Monotonic request counter (`currentSummaryRequestId`) preventing stale out-of-order responses from overwriting active state when switching shops.
  * Automatic summary refresh triggered immediately after user review creation, editing, or deletion.
* **AI-Generated "Must Try" Recommendations**:
  * Non-blocking "Must Try" recommendation card within `ShopDetailCard`.
  * Asynchronous background fetching initiated after shop selection alongside review summaries.
  * Displays specific menu and beverage recommendations grounded in actual customer reviews, pairing each item with a concise reason for the recommendation.
  * Review count attribution banner indicating how many customer reviews were evaluated.
  * Distinct semantic UI states driven by backend status enums:
    * `insufficient_reviews`: renders *"✨ Not enough customer reviews yet to generate recommendations."* when usable review count is $< 3$.
    * `available` with 0 items: renders *"✨ No specific menu recommendations found in the available reviews."* when 3+ usable reviews exist but contain no positive item mentions.
    * `available` with $>0$ items: renders the full "Must Try" card with recommended item list.
  * Error state presentation with localized retry button.
  * Monotonic request counter (`currentRecommendationsRequestId`) discarding out-of-order responses and preventing stale recommendations from displaying when rapidly switching shops.
  * Automatic recommendation refresh triggered immediately after user review creation, editing, or deletion.
* Interactive map visualization via `react-native-maps`.
* Device foreground location permission requests via `expo-location`.
* Automatic user coordinate acquisition and map re-centering.
* Current user location representation through native map location indicators.
* Sensible fallback region (Metro Manila) when location access is pending or unavailable.
* Graceful, non-crashing permission denial handling with informative status banners.
* Terminal permission denial handling (`canAskAgain: false`) with direct system settings navigation via `Linking.openSettings()`.
* Authenticated nearby coffee shop discovery based on the user's coordinates.
* Map markers for discovered coffee shops.
* Nearby coffee shop list/bottom-sheet presentation.
* Coffee shop selection and detail presentation.
* Loading, empty, location-error, and API-error states for discovery.
* Protection against stale asynchronous discovery responses.
* Authenticated external review retrieval through the FastAPI backend.
* External review display within the coffee shop detail experience with provider attribution and source links.
* **First-Party LOKAL Review Capabilities**:
  * Authenticated retrieval and display of first-party LOKAL reviews.
  * Separate LOKAL Community rating score and review count displayed alongside external ratings.
  * Review cards displaying author display name, star rating (1–5), publication timestamp, `(Edited)` indicator, and optional review text.
  * Dedicated "Your Review" section displaying the authenticated user's current review with Edit and Delete actions.
  * Review creation and editing modal supporting interactive 1–5 star rating selection, optional review text with character count (max 1000 characters), and validation feedback.
  * Review deletion flow with confirmation dialog and error handling.
  * Full optimistic UI updates and localized error banner display with retry capabilities.
* **Stale Async & Mutation Race Protection**:
  * Monotonic request counters (`currentRequestId`, `currentSummaryRequestId`, `currentRecommendationsRequestId`, `currentFavoriteRequestId`) and mutation counters (`currentMutationId`, `currentFavoriteMutationId`) in `ShopDetailCard` ensuring late-arriving responses or mutations from previously selected shops or previous auth sessions are discarded.
  * Component lifecycle keying in `NearbyShopsSheet` (`${selectedShop.id}:${authToken || 'anon'}`) ensuring complete reset of review form, submission, deletion, summary, recommendation, and favorite states on shop selection change.
* Non-blocking review loading and retry behavior.
* Zero external UI dependencies, maintaining scope discipline and clean architecture.

Background location tracking remains outside the current implementation scope.

---

# Current Backend Capabilities

The FastAPI backend currently provides:

* Application configuration through environment variables (including `GEMINI_API_KEY` and `GEMINI_MODEL`).
* Basic health-check endpoints (`/health` and `/api/v1/health`).
* Supabase client initialization through `backend/app/core/supabase.py` with lazy loading, HTTPS enforcement, and isolated request-scoped authenticated client instantiation (`create_scoped_supabase_client`).
* Database schema migrations located in `supabase/migrations/`:
  * `20260811000000_initial_schema.sql`: Core tables, PostGIS extensions, shops, and nearby search RPC.
  * `20260919000000_user_reviews.sql`: First-party user reviews schema, constraints, RLS policies, table privilege hardening, and secure write RPCs.
  * `20260930000000_favorite_coffee_shops.sql`: Favorites schema, unique constraints, RLS policies, table privilege hardening, and secure `create_user_favorite` RPC.
  * `20261001000000_harden_public_schema_and_rls.sql`: Row Level Security enablement across all six public tables, least-privilege table and column grants, revocation of direct client shop mutations, and column-level curation protection.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Dedicated service-role database client (`backend/app/core/supabase.py`) and fail-closed FastAPI dependency `get_service_role_supabase()` (`backend/app/api/deps.py`) requiring `SUPABASE_SERVICE_ROLE_KEY` and returning `HTTP 503` if unconfigured.
* Authenticated coffee shop management via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`):
  * Public/authenticated read access for approved coffee shops.
  * Privileged shop mutations (`POST`, `PATCH`, `DELETE`) protected by `require_curator` and executed through `get_service_role_supabase()`. Direct client PostgREST mutations are denied.
* Authenticated nearby coffee shop discovery via `GET /api/v1/shops/nearby`.
* Independent business eligibility and curation layer (`APPROVED`, `EXCLUDED`, `PENDING_REVIEW`):
  * Curation inspection (`GET /api/v1/shops/{id}/curation`) and evaluation (`POST /api/v1/shops/{id}/curation/evaluate`) protected by `require_curator` and executed via `get_service_role_supabase()`.
  * Column-level grant protection ensuring direct Data API callers can only query `(shop_id, status)` for approved shops without exposing internal notes or confidence scores.
* **Favorite Coffee Shops Management & Endpoints**:
  * `GET /api/v1/shops/{shop_id}/favorite`: Checks caller's favorite status for an approved coffee shop; returns `FavoriteStatusResponse(shop_id, is_favorite, favorited_at)`. Returns `404 Not Found` if the shop does not exist or is not `APPROVED`.
  * `POST /api/v1/shops/{shop_id}/favorite`: Adds the shop to caller's favorites via PostgreSQL RPC `create_user_favorite`. Returns `201 Created` on new favorite or `200 OK` if already favorited (idempotent). Fails closed with `404 Not Found` if shop is not `APPROVED`.
  * `DELETE /api/v1/shops/{shop_id}/favorite`: Idempotently removes shop from caller's favorites (`204 No Content`).
  * Scoped authenticated Supabase client propagation carrying caller's JWT for RLS and RPC execution.
  * Fail-closed curation validation in `FavoriteService`: defaults missing curation records to `PENDING_REVIEW` and surfaces Supabase `APIError` and unexpected exceptions as HTTP 500 without masking database infrastructure failures.
* **Unified Review Layer & Endpoints**:
  * `GET /api/v1/shops/{shop_id}/reviews`: Returns normalized unified reviews (LOKAL first-party reviews first, followed by external reviews) with separate LOKAL and external rating metrics. Returns `404 Not Found` if the shop is `PENDING_REVIEW` or `EXCLUDED`.
  * `POST /api/v1/shops/{shop_id}/reviews`: Submits a first-party review for an approved shop, enforcing the 1-review-per-user constraint, 1–5 rating range, and max 1000 characters content.
  * `GET /api/v1/shops/{shop_id}/reviews/mine`: Retrieves the authenticated caller's own review; permitted even if the shop is `PENDING_REVIEW` or `EXCLUDED`.
  * `PATCH /api/v1/shops/{shop_id}/reviews/mine`: Partially updates caller's review with field-presence semantics; blocked if shop is not approved; permits text clearing via `null` or empty string.
  * `DELETE /api/v1/shops/{shop_id}/reviews/mine`: Permanently deletes caller's review; permitted even if shop is `PENDING_REVIEW` or `EXCLUDED`.
* **AI Review Summarization Layer & Endpoint**:
  * `GET /api/v1/shops/{shop_id}/reviews/summary`: Protected endpoint returning structured AI review summary for an approved coffee shop.
  * `ReviewSummarizer` (Protocol) abstraction enabling clean decoupling from specific AI vendors.
  * `GeminiReviewSummarizer` implementation targeting Google Gemini REST API (`gemini-2.5-flash`) via `httpx`, with `thinkingBudget: 0` to preserve the output token budget for JSON synthesis.
  * Application-level Pydantic schema validation boundary (`ReviewSummaryContent`), failing closed on malformed output or non-`STOP` finish reasons.
  * Privacy-preserving review sanitization: strips author names and internal IDs, passes only rating and truncated text within `<reviews>` XML tags with anti-prompt-injection system instructions.
  * 3-review minimum usable text threshold check; excludes rating-only reviews.
  * `InMemorySummaryCache` (1-hour TTL, 500 capacity) with thread-safe per-shop generation tracking preventing in-flight stale cache repopulation.
  * Automatic cache invalidation and generation advancement on first-party review creation, editing, and deletion.
* **AI Must-Try Recommendation Layer & Endpoint**:
  * `GET /api/v1/shops/{shop_id}/reviews/recommendations`: Protected endpoint returning structured AI "Must Try" menu and beverage recommendations for an approved coffee shop.
  * `ReviewRecommender` (Protocol) abstraction decoupling recommendation generation from specific AI vendors.
  * `GeminiReviewRecommender` implementation targeting Google Gemini REST API via `httpx`, with header-based API key auth (`x-goog-api-key`) and model-specific generation configurations (`thinkingBudget: 0` for `gemini-2.5-flash`; `thinkingBudget: 1024` for `gemini-2.5-pro`; omitted for legacy models).
  * Internal evidence contract (`InternalRecommendationContent`) capturing item name, reason, supporting review index, and verbatim review evidence excerpt.
  * Application-level five-point grounding validation boundary (`validate_and_convert_recommendations`): verifies review index bounds, referenced review rating $\ge 4.0$, verbatim evidence substring match, item token containment, and phrase-aware negative context heuristic with bounded negator scanning.
  * Per-item validation: filters individual ungrounded recommendations and returns valid items; returns HTTP 200 with `items=[]` if all items fail grounding; strips internal evidence fields before returning public response (`RecommendationItem`).
  * 3-review minimum usable text threshold check; returns `status: "insufficient_reviews"` when fewer than 3 reviews are available.
  * `InMemoryRecommendationCache` (1-hour TTL, 500 capacity) with thread-safe per-shop generation tracking preventing stale cache repopulation.
  * Automatic cache invalidation and generation advancement on first-party review creation, editing, and deletion.
* **Database Write Privilege Protection & Secure RPCs**:
  * Direct PostgREST `INSERT` and `UPDATE` on `reviews` and `favorites` revoked; writes routed through PostgreSQL `SECURITY DEFINER` RPCs (`create_user_review`, `update_user_review`, `create_user_favorite`) with `auth.uid()` derivation and revoked `PUBLIC` execution privileges.
  * Immutable author name snapshotting from user metadata with fallback to `'LOKAL User'`. Never exposes user emails or internal UUIDs in review responses.
  * Strict `source = 'lokal'` filtering across application review lookups, updates, and deletes.
* Google Places API (New) integration for transient external review retrieval with provider attribution and source links. No caching or persistence of Google review content.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), external provider failures (`502`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **297 passing tests**, covering auth, shops, curation, nearby discovery, external reviews, first-party user reviews, AI review summaries, AI must-try recommendations, favorite coffee shops, curator authorization, and service-role fail-closed behavior.

---

# Current Database & Security Architecture

The database is managed through PostgreSQL in Supabase with full Row Level Security (RLS) and controlled stored procedures across all public schema tables:

* **Tables**:
  * `shops`: Core coffee shop details (name, address, coordinates, Google Place ID, etc.).
  * `shop_curation`: Business eligibility status (`APPROVED`, `EXCLUDED`, `PENDING_REVIEW`), observed location counts, evidence metadata, confidence scores, and curator notes.
  * `shop_curation_audit`: Append-only curation audit log capturing status transitions, timestamps, reasons, and curator IDs.
  * `menu_items`: Coffee shop menu items (internal/service-role access only).
  * `reviews`: Stores first-party LOKAL user reviews and historical/external review metadata.
  * `favorites`: Stores authenticated user favorite coffee shops with uniqueness constraints and foreign key cascade deletions.
* **Least-Privilege Table & Column Grants**:
  * `shops`: `SELECT` granted to `anon` and `authenticated`. All direct client write grants (`INSERT`, `UPDATE`, `DELETE`) are revoked. Full `ALL` access granted strictly to `service_role`.
  * `shop_curation`: Direct table `SELECT` revoked from `anon`, `authenticated`, and `public`. Column-level `SELECT (shop_id, status)` granted to `anon` and `authenticated`. Sensitive columns (`curator_notes`, `evidence_source`, `confidence`, `curator_id`, `location_count`) are restricted from client roles. Full access granted strictly to `service_role`.
  * `menu_items`: All privileges revoked from `anon`, `authenticated`, and `public`. Granted strictly to `service_role`.
  * `shop_curation_audit`: All privileges revoked from `anon` and `public`. `SELECT` granted to `authenticated`. Full access granted strictly to `service_role`.
  * `reviews`: Direct `INSERT` and `UPDATE` revoked from client roles. `SELECT` and `DELETE` granted to `authenticated`. Full access granted to `service_role`.
  * `favorites`: Direct `INSERT` and `UPDATE` revoked from client roles. `SELECT` and `DELETE` granted to `authenticated`. Full access granted to `service_role`.
* **Row Level Security (RLS) Policies**:
  * `shops`:
    * Public/Authenticated `SELECT`: Allowed for coffee shops where `shop_curation.status = 'APPROVED'`, or where JWT `(auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')`.
    * Mutations: Direct client mutations are blocked; mutations must proceed via FastAPI gateway using `service_role`.
  * `shop_curation`:
    * Public/Authenticated `SELECT`: Allowed where `status = 'APPROVED'`, or where JWT role is curator/admin.
    * Full access granted to `service_role`.
  * `menu_items`:
    * Full access granted strictly to `service_role`.
  * `shop_curation_audit`:
    * Authenticated `SELECT`: Allowed only where JWT `(auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')`.
    * Full access granted to `service_role`.
  * `reviews`:
    * `SELECT`: Authenticated users can select reviews for coffee shops with `shop_curation.status = 'APPROVED'` or their own reviews (`auth.uid() = user_id`).
    * `DELETE`: Authenticated users can delete only their own reviews (`auth.uid() = user_id`).
  * `favorites`:
    * `SELECT`: Authenticated users can select only their own favorites (`auth.uid() = user_id`).
    * `DELETE`: Authenticated users can delete only their own favorites (`auth.uid() = user_id`).
* **Review Schema & Integrity**:
  * `user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE`
  * `author_name TEXT NOT NULL DEFAULT 'LOKAL User'`
  * `source TEXT NOT NULL DEFAULT 'lokal'`
  * `uq_reviews_user_shop UNIQUE (user_id, shop_id)`: Enforces single review per user per coffee shop.
  * Indexes: `idx_reviews_shop_id` and `idx_reviews_user_id`.
* **Favorite Schema & Integrity**:
  * `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  * `shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE`
  * `created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())`
  * `uq_favorites_user_shop UNIQUE (user_id, shop_id)`: Enforces single favorite record per user per coffee shop.
  * Indexes: `idx_favorites_user_shop ON favorites (user_id, shop_id)`.
* **Controlled Security Definer RPCs**:
  * `create_user_review(p_shop_id, p_rating, p_content)`: Validates rating (1–5), verifies shop existence and `APPROVED` curation status, enforces uniqueness, resolves author display name snapshot from user profile metadata, and inserts review with server timestamps.
  * `update_user_review(p_shop_id, p_rating, p_content, p_update_content)`: Enforces field presence, validates rating, verifies shop is `APPROVED`, enforces caller ownership and `source = 'lokal'`, preserves server-managed fields, and updates `rating`, `content`, and `updated_at`.
  * `create_user_favorite(p_shop_id)`: Validates caller authentication (`auth.uid() IS NOT NULL`), verifies target shop existence and `APPROVED` curation status in `shop_curation`, inserts favorite record with server-derived `auth.uid()`, and handles duplicate conflicts idempotently.
  * Stored procedure execution privileges are revoked from `PUBLIC` and granted strictly to `authenticated`.
* **Automated Database Test Suite (`supabase/tests/01_rls_and_permissions.sql`)**:
  * Executable pgTAP test suite containing **55 planned assertions** verifying RLS flags, table permissions, column privileges, and allow/deny query behaviors for `anon`, ordinary `authenticated`, and curator roles.

---

# Current Data / AI Architecture Direction

The project implements a hybrid review-data architecture with operational AI review summarization and grounded menu recommendations:

```text
Google Places Reviews (external, transient)
                  +
       LOKAL User Reviews (first-party, persisted in Supabase)
                  ↓
          FastAPI Review Layer
                  ↓
         Unified Review Domain
                  ↓
                AI Layer
  (ReviewSummaryService & ReviewRecommendationService / Gemini)
                  ↓
             LOKAL Mobile
```

The external review layer retrieves reviews from Google Places API (New) on demand. External review content is transient and is not persisted or cached in Supabase, preserving provider attribution and policy compliance.

First-party LOKAL reviews are persisted in Supabase with author name snapshotting, rating constraints, single-review uniqueness, and RLS/RPC security.

The review domain merges first-party LOKAL reviews and external reviews into a unified provider-neutral representation (`UnifiedReview`), exposing separate external and community metrics so downstream consumers can clearly distinguish first-party feedback.

The AI layer ingests sanitized reviews from the unified review domain to generate structured review summaries (`ReviewSummaryService`) and AI-grounded "Must Try" menu recommendations (`ReviewRecommendationService`), using `GeminiReviewSummarizer` and `GeminiReviewRecommender` via HTTP requests to Google Gemini API. Summaries and recommendations are cached in-memory with a 1-hour TTL and generation-guarded invalidation, without creating persistent summary or recommendation database tables.

Independent-business eligibility and curation are maintained as a separate domain concern, ensuring review, AI, and favorite operations respect public discovery eligibility rules (`APPROVED` required).

---

# Next Task

The next feature should be defined through the next GitHub Issue after reviewing the completed favorite coffee shops architecture and current application state.

With user authentication, unified reviews, AI review summarization, AI must-try recommendations, and coffee shop favoriting active, the logical next capabilities include **User Favorites List / Profile Discovery** (viewing and navigating through the user's saved favorite coffee shops), **Advanced Search and Filtering** (filtering by rating, distance, or favorites), or another feature prioritized by the Product Owner.

Before implementation:

1. Review the current database schema, curation layer, review service, favorites service, AI services, and mobile components.
2. Define the product requirement and observable acceptance criteria for the next capability.
3. Review dependencies, latency implications, and data modeling trade-offs.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

The unified review domain, AI review summarization, AI-generated "Must Try" recommendations, and coffee shop favoriting are operational. External reviews remain transient and compliant with provider policies, while first-party reviews and user favorites are securely persisted in Supabase with RLS and security-definer RPC protection. In-memory caching with generation versioning is active for both summaries and recommendations. Mobile user authentication, review mutations, non-blocking summary cards, non-blocking recommendations cards, and interactive favorite toggles are operational and fully tested.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **Database Write Privilege Revocation over PostgREST**: Row Level Security (RLS) alone does not replace table-level grants. When mutations must enforce business logic (such as curator authorization, evidence recalculation, and audit logging), revoking table-level `INSERT`, `UPDATE`, and `DELETE` from client roles (`anon`, `authenticated`) eliminates PostgREST bypasses, ensuring mutations proceed strictly through the trusted FastAPI gateway.
* **Fail-Closed Dedicated Service-Role Dependency**: Privileged server operations requiring database superuser or bypass privileges must not rely on clients that can fall back to the public `anon` key. Using a dedicated dependency (`get_service_role_supabase()`) that strictly validates `SUPABASE_SERVICE_ROLE_KEY` and raises HTTP 503 if unconfigured enforces fail-closed infrastructure guarantees.
* **Column-Level Privilege Granularity for Public Schemas**: Sensitive metadata (e.g., internal curator notes, confidence scores, evidence sources) on otherwise readable public tables should be restricted via column-level `GRANT SELECT (shop_id, status)` to prevent exposure through direct PostgREST queries.
* **Executable Database-Level Authorization Testing**: Database authorization test suites must not rely solely on metadata introspection (e.g. `pg_class.relrowsecurity`). Testing executable `SELECT`, `INSERT`, `UPDATE`, and `DELETE` queries under `SET LOCAL ROLE` with simulated JWT claims (`auth.uid()`, `auth.jwt()`) verifies actual allow/deny behavior and row isolation against real database execution.
* **Discrete Unknown State in Toggle Controls**: Boolean toggle buttons (`isFavorite`) must not default to `false` when initial status retrieval is asynchronous. Using `null` to represent unconfirmed status ensures controls remain disabled during initial load or network failures, preventing erroneous mutation requests from executing against unverified states.
* **In-Banner Retry Recovery for Disabled Controls**: When a component disables an interactive control because its initial state could not be loaded, the associated error presentation must offer an actionable retry mechanism so users are not stranded in a permanently disabled state without navigating away.
* **Fail-Closed Curation Checking on Secondary Operations**: Auxiliary features (such as favorites or reviews) that depend on parent entity curation status must fail closed on missing curation records or database communication failures (`APIError`), treating unknown states as unapproved or error conditions rather than allowing unauthorized mutations.
* **Atomic Database-Level Favoriting with RPCs**: Routing favorite creation through a PostgreSQL `SECURITY DEFINER` RPC enforces curation requirements and uniqueness atomically at the database layer while automatically binding `auth.uid()`, preventing race conditions and bypassing client manipulation.
* **Per-Item Grounding Validation**: LLM-generated recommendations must be grounded strictly against the source reviews. Validating supporting review index, rating threshold ($\ge 4.0$), verbatim evidence substring presence, item token presence in evidence, and negative-context heuristic checks on an individual item basis ensures hallucinations or ungrounded claims are dropped without failing the entire response.
* **Phrase-Aware Bounded Negator Scanning**: When evaluating candidate evidence for negative context (e.g. `avoid`, `skip`, `burnt`), scanning backward for negators must be bounded to immediate preceding tokens or permitted connector phrases (e.g. `at all`, `being`, `to be`). Scanning unbounded windows or ignoring punctuation resets risks falsely treating a negator for an earlier clause (e.g. `not fresh, stale` or `no milk, burnt`) as negating the target descriptor.
* **Model-Specific Reasoning Budget Configuration**: Different Gemini models handle `thinkingConfig` differently; while `gemini-2.5-flash` requires `thinkingBudget: 0` to prevent reasoning token starvation of output tokens, other models (such as `gemini-2.5-pro`) may require a positive budget (e.g. `1024`) or omit the field. Provider implementations should adapt the request payload dynamically based on the configured model name.
* **Header-Based AI Provider Authentication**: Passing external API keys via request headers (`x-goog-api-key`) rather than URL query parameters prevents credential leakage in server logs, proxy logs, and HTTP tracebacks.
* **Semantic State Distinction in Client AI Cards**: Distinct product states (e.g. `insufficient_reviews` vs `available` with 0 recommendations vs `available` with $>0$ recommendations) should be represented explicitly in domain status fields rather than inferred from array lengths alone, ensuring unambiguous UI rendering and messaging.
* **Generation-Guarded In-Memory Caching**: When caching asynchronous LLM responses in memory without a persistent database, protect the cache with an atomic generation/version check. Long-running in-flight summarization or recommendation requests must not write back stale pre-mutation data if an invalidation occurred while the request was in flight.
* **Application-Level Validation Boundary for LLM Outputs**: Never rely solely on vendor "structured output" flags or schema requests. Always validate the returned content with Pydantic (`ReviewSummaryContent.model_validate_json` / `InternalRecommendationContent.model_validate_json`) and fail closed to HTTP 502 Bad Gateway if the model returns malformed, incomplete, or schema-nonconforming responses.
* **Dedicated Reasoning Budget Control on LLM Providers**: For bounded structured JSON synthesis tasks on thinking-enabled models (such as `gemini-2.5-flash`), explicitly configure `"thinkingConfig": {"thinkingBudget": 0}` to disable internal reasoning tokens so they do not exhaust the `maxOutputTokens` allocation and trigger unintended `MAX_TOKENS` truncations.
* **Deterministic Race-Condition Testing with Controlled Promises**: Replace arbitrary `setTimeout` delays in asynchronous race tests with manually resolvable promises (`shopAPromise`). This guarantees deterministic test execution regardless of event-loop timing or test environment CPU load.
* **Fail-Closed Provider Shape Parsing**: Wrap raw provider JSON parsing and dictionary/list extraction in explicit exception handlers (`ValueError`, `TypeError`, `AttributeError`, `KeyError`, `IndexError`) to convert unexpected upstream provider shapes into sanitized `ExternalProviderError` (mapped to HTTP 502) rather than unhandled 500 server errors.
* **Safe Provider Error Logging**: Log only non-sensitive diagnostic metadata (e.g. HTTP status codes and safe error categories). Never dump raw `response.text`, user review text, or request payloads in server logs.
* **Monotonic Generation Guards for Async State Transitions**: Protect complex client-side authentication and session flows (restoration, retry, login, logout) with a monotonic generation ref that increments on each new operation and at the completion of critical cleanup in `finally` blocks. This ensures stale or out-of-order async responses never overwrite state or reintroduce credentials.
* **Fail-Safe Client Credential Purging**: Local credential deletion on logout must be executed inside a `finally` block so that network failures, timeouts, or backend 5xx errors never trap the user in an authenticated local state.
* **Strict Runtime Security Invariants**: Never allow production applications to silently fall back from hardware-backed secure storage (e.g. `expo-secure-store`) to in-memory storage; fallbacks must be strictly isolated to headless test harnesses.
* **Fixed Request Timeouts on Auth Operations**: Bounding authentication HTTP requests with fixed timeouts (`AbortController`) prevents the application from hanging indefinitely in transient restoration or login states during network degradation.
* **Session Restoration Error Differentiation**: Differentiating permanently invalid credentials (`401 Unauthorized`, which warrants credential purging) from transient connection/server failures (which warrants credential preservation and actionable retry/sign-out controls) prevents accidental session destruction while keeping users in control.
* **Database Write Privilege Hardening**: Sensitive database tables should have direct `INSERT` and `UPDATE` privileges revoked from client roles (including `authenticated`). Routing writes through PostgreSQL `SECURITY DEFINER` RPCs protects server-managed fields (`user_id`, `author_name`, `source`, `created_at`) from client tampering.
* **RPC Execution Privilege Revocation**: PostgreSQL functions grant execute permissions to `PUBLIC` by default. Security-definer RPCs must explicitly revoke execution from `PUBLIC` and grant execute strictly to `authenticated`.
* **Source Isolation in Multi-Source Tables**: When a table stores records originating from multiple sources (such as first-party and external/legacy data), all query, update, and delete operations must explicitly scope themselves to `source = 'lokal'` to prevent cross-contamination.
* **Author Privacy & Snapshotting**: Review author identity should be resolved on the server from profile metadata (`full_name`/`display_name`) and snapshot at review creation time, defaulting to a privacy-preserving fallback (`'LOKAL User'`). User email addresses and internal UUIDs must never be exposed.
* **Lifecycle Keying & Async Race Protection in Mobile**: Using compound component keys (`shop.id:authToken`) on child detail cards combined with monotonic request and mutation sequence counters prevents stale async fetch results and in-flight mutation errors from leaking across shop selection changes.
* **Curation-Aware Review Policy**: Review creation, editing, and public listing should be strictly aligned with shop curation status (`APPROVED` required), while ensuring users retain full ownership and deletion rights for their existing reviews even if a shop becomes `EXCLUDED`.
* **Metric Separation in Unified Domains**: Preserving separate provider and community rating metrics (`average_rating` vs `lokal_average_rating`) provides transparency and provenance without introducing premature composite scoring algorithms.
* **Request-Scoped Supabase Client**: PostgREST queries should carry the caller's JWT rather than relying on a shared anonymous session so that Row Level Security (RLS) policies and RPCs can identify `auth.uid()`.
* **REST Semantic Discipline**: Distinguishing between client-caused validation errors (`400`/`422`), nonexistent resources (`404`), unique constraint violations (`409`), external provider failures (`502`), service unavailability (`503`), and unexpected server-side errors (`500`) yields predictable API behavior.
* **Fail-Closed Eligibility**: Business eligibility and public discovery should default to hidden/pending when evidence is insufficient rather than risk exposing unsupported businesses.
* **Human-Controlled Merge**: Agy prepares and validates changes, while the Product Owner performs the final review and merge.
* **Current-State Discipline**: `CURRENT_STATE.md` describes `main` only and is updated after changes are merged.

---

# Development Session Reminder

Every new feature should begin by following the workflow defined in:

* `docs/workflow.md`
* `AGENTS.md`

Before implementation:

1. `git checkout main`
2. `git pull origin main`
3. `git status` — working tree must be clean.
4. Verify `docs/CURRENT_STATE.md` reflects `main`.
5. Review the assigned GitHub Issue.
6. Review `README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/workflow.md`, and `docs/CURRENT_STATE.md`.
7. Review architecture and external dependencies when required.
8. Present the implementation plan.
9. Obtain Product Owner approval.
10. Agy creates the feature branch.
11. Begin implementation strictly within approved scope.

After implementation:

1. Run required automated tests and local verification.
2. Commit and push the feature branch.
3. Open the Pull Request.
4. Evaluate and resolve CodeRabbit findings iteratively.
5. Product Owner performs final review and merges the Pull Request.
6. Synchronize local `main`.
7. Update `docs/CURRENT_STATE.md` to reflect the merged state.
8. Commit and push the documentation update.
9. Confirm the working tree is clean.

---

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #37 and merge of PR #38)
