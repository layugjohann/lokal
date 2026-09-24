# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, independent business eligibility and curation, external review data layer, and first-party LOKAL user reviews are established.

The project is now building application-level features that provide the foundation for LOKAL's future AI capabilities, including AI review summaries and recommendations.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed feature, **Coffee Shop Search, Filtering, and Sorting (GitHub Issue #27)**, enhances the nearby discovery domain with debounced name search, distance preset filtering (1 km, 3 km, 5 km), minimum rating filtering (4.0+, 4.5+), and configurable sort ordering (Nearest vs. Top Rated). The SQL RPC (`get_nearby_shops`) executes bounding box pruning, Haversine distance calculation, escaped wildcard pattern matching (`ESCAPE E'\\'`), and deterministic tie-breaker sorting under `SECURITY INVOKER` privileges while preserving fail-closed business curation filtering (`APPROVED` only).

The mobile application provides an interactive discovery sheet with search input, horizontal filter chips, active filter indicators, one-tap filter reset, and robust protection against asynchronous race conditions and location loss. First-party user reviews (GitHub Issue #24) remain fully integrated into the coffee shop detail card alongside transient external Google reviews.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #27 — Coffee Shop Search, Filtering, and Sorting

**Status:** ✅ Completed

### Completed Work

* **Database Migration & Stored Procedure**:
  * Created migration `supabase/migrations/20260923000000_shop_search_and_filters.sql` updating `get_nearby_shops` with optional discovery parameters: `search_query TEXT DEFAULT NULL`, `min_rating DOUBLE PRECISION DEFAULT NULL`, and `sort_by TEXT DEFAULT 'distance'`.
  * Implemented case-insensitive name filtering (`s.name ILIKE ...`) with robust wildcard escaping for `%`, `_`, and `\` using PostgreSQL `ESCAPE E'\\'`.
  * Added rating filtering evaluated against the existing `shops.rating` column (`min_rating IS NULL OR s.rating >= min_rating`).
  * Implemented deterministic sorting with tie-breakers:
    * `distance` (default): `ORDER BY distance_meters ASC, id ASC`.
    * `rating`: `ORDER BY rating DESC NULLS LAST, distance_meters ASC, id ASC`.
  * Preserved the `SECURITY INVOKER` security model and enforced strict eligibility checking (`shop_curation.status = 'APPROVED'`).
* **Backend API Endpoints**:
  * Updated `GET /api/v1/shops/nearby` in `backend/app/api/v1/endpoints/shops.py`:
    * Added `query: Optional[str] = Query(default=None, min_length=1, max_length=100)`: sanitizes whitespace and forwards as `search_query` to the RPC.
    * Added `min_rating: Optional[float] = Query(default=None, ge=0.0, le=5.0)`: filters shops by rating threshold.
    * Added `sort_by: str = Query(default="distance", pattern="^(distance|rating)$")`: enforces strict lowercase validation, returning HTTP 422 for unsupported or uppercase values.
* **Mobile Application Integration**:
  * Integrated a search bar with clear button and 350ms debounced text input into `NearbyShopsSheet`.
  * Added interactive horizontal filter chip bar supporting:
    * Distance presets: 1 km, 3 km, 5 km (tapping active chip toggles back to 5 km default).
    * Rating presets: ★ 4.0+, ★ 4.5+ (tapping active chip clears rating filter).
    * Sort criteria: Nearest vs. Top Rated.
  * Added active filter detection with header "Reset" button and empty state "Reset Filters" action.
  * Preserved selection state across refreshed search/filter results if the selected shop remains present; clears selection if the shop is filtered out.
  * Enhanced `useNearbyShops` with monotonic request counter (`requestIdRef`) protecting against out-of-order responses and search keystroke race conditions.
  * Resolved in-flight request lifecycle race by explicitly invalidating in-flight requests on location loss (`location == null`), ensuring stale responses cannot repopulate state.
  * Zero external UI dependencies, maintaining scope discipline and clean architecture.
* **Automated Verification**:
  * Completed backend verification with **193 unit/regression tests passing** in 1.3s (including 11 dedicated search, filter, and sort tests in `test_nearby_shops.py`).
  * Completed mobile verification with **32 automated tests passing** in 250ms (including query serialization, filter chip toggle logic, debouncing, keystroke race handling, and location loss invalidation).
  * Completed TypeScript verification with **0 errors** (`npx tsc --noEmit`).
* **Pull Request**:
  * Pull Request #28 was reviewed by CodeRabbit, actionable findings were resolved (wildcard escaping and location-loss in-flight request invalidation), and the PR is prepared for Product Owner review and merge.

---

# Project Progress

| Feature / Milestone                              | Status      |
| ------------------------------------------------ | ----------- |
| Engineering Foundation                           | ✅ Complete |
| Issue #1 — Initialize Mobile Application         | ✅ Complete |
| Issue #3 — Initialize FastAPI Backend            | ✅ Complete |
| Issue #5 — Initialize Supabase Integration       | ✅ Complete |
| Issue #7 — Database Schema                       | ✅ Complete |
| Issue #9 — User Authentication                   | ✅ Complete |
| Issue #11 — Maps & Location Integration          | ✅ Complete |
| Issue #13 — Coffee Shop CRUD API                 | ✅ Complete |
| Issue #15 — Coffee Shop Discovery & Search       | ✅ Complete |
| Issue #19 — External Review Data Layer            | ✅ Complete |
| Issue #22 — Independent Business Eligibility & Shop Curation | ✅ Complete |
| Issue #24 — LOKAL User Reviews                   | ✅ Complete |
| Issue #27 — Coffee Shop Search, Filtering, and Sorting | ✅ Complete |
| AI-Assisted Engineering Workflow                 | ✅ Complete |
| AI Review Summaries                              | ⏳ Planned  |
| AI Must-Try Recommendations                      | ⏳ Planned  |

---

# Current Mobile Capabilities

The React Native (Expo) mobile application currently provides:

* Interactive map visualization via `react-native-maps`.
* Device foreground location permission requests via `expo-location`.
* Automatic user coordinate acquisition and map re-centering.
* Current user location representation through native map location indicators.
* Sensible fallback region (Metro Manila) when location access is pending or unavailable.
* Graceful, non-crashing permission denial handling with informative status banners.
* Terminal permission denial handling (`canAskAgain: false`) with direct system settings navigation via `Linking.openSettings()`.
* Authenticated nearby coffee shop discovery based on the user's coordinates.
* Map markers for discovered coffee shops with selection sync and coordinate re-centering.
* Nearby coffee shop list/bottom-sheet presentation.
* Coffee shop selection and detail presentation.
* Loading, empty, location-error, and API-error states for discovery.
* Protection against stale asynchronous discovery responses using monotonic sequence counters.
* Immediate in-flight request cancellation on location loss, preventing stale responses from repopulating state.
* **Search, Filtering, and Sorting Capabilities**:
  * Search coffee shops by name with 350ms input debouncing and clear button.
  * Distance preset filters (1 km, 3 km, 5 km) with toggle-to-default behavior.
  * Rating filters (★ 4.0+, ★ 4.5+) filtering by minimum rating.
  * Sort criteria toggling between Nearest and Top Rated.
  * Active filter detection badge with header "Reset" and empty-state "Reset Filters" action.
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
  * Monotonic request counter (`currentRequestId`) and mutation counter (`currentMutationId`) in `ShopDetailCard` ensuring late-arriving responses or mutations from previously selected shops or previous auth sessions are discarded.
  * Component lifecycle keying in `NearbyShopsSheet` (`${selectedShop.id}:${authToken || 'anon'}`) ensuring complete reset of review form, submission, and deletion states on shop selection change.
* Non-blocking review loading and retry behavior.
* Zero external UI dependencies, maintaining scope discipline and clean architecture.

AI review summaries, Must-Try recommendations, and background location tracking remain outside the current implementation scope.

---

# Current Backend Capabilities

The FastAPI backend currently provides:

* Application configuration through environment variables.
* Basic health-check endpoints (`/health` and `/api/v1/health`).
* Supabase client initialization through `backend/app/core/supabase.py` with lazy loading, HTTPS enforcement, and isolated request-scoped authenticated client instantiation (`create_scoped_supabase_client`).
* Database schema migrations located in `supabase/migrations/`:
  * `20260811000000_initial_schema.sql`: Core tables, PostGIS extensions, shops, and nearby search RPC.
  * `20260916000000_nearby_shops_rpc.sql`: Initial nearby discovery stored procedure with bounding box and Haversine distance.
  * `20260918000000_shop_curation.sql`: Independent business eligibility and curation schema (`shop_curation`, audit trail).
  * `20260919000000_user_reviews.sql`: First-party user reviews schema, constraints, RLS policies, table privilege hardening, and secure write RPCs.
  * `20260923000000_shop_search_and_filters.sql`: Enhanced `get_nearby_shops` SQL RPC with search query, minimum rating, and sort ordering.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Authenticated coffee shop management via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`).
* Authenticated nearby coffee shop discovery via `GET /api/v1/shops/nearby` supporting optional `query` (name search), `min_rating` (threshold filter), and `sort_by` (strict lowercase validation: `distance` or `rating`).
* Independent business eligibility and curation layer (`APPROVED`, `EXCLUDED`, `PENDING_REVIEW`) with fail-closed rules and audit trail.
* **Unified Review Layer & Endpoints**:
  * `GET /api/v1/shops/{shop_id}/reviews`: Returns normalized unified reviews (LOKAL first-party reviews first, followed by external reviews) with separate LOKAL and external rating metrics. Returns `404 Not Found` if the shop is `PENDING_REVIEW` or `EXCLUDED`.
  * `POST /api/v1/shops/{shop_id}/reviews`: Submits a first-party review for an approved shop, enforcing the 1-review-per-user constraint, 1–5 rating range, and max 1000 characters content.
  * `GET /api/v1/shops/{shop_id}/reviews/mine`: Retrieves the authenticated caller's own review; permitted even if the shop is `PENDING_REVIEW` or `EXCLUDED`.
  * `PATCH /api/v1/shops/{shop_id}/reviews/mine`: Partially updates caller's review with field-presence semantics; blocked if shop is not approved; permits text clearing via `null` or empty string.
  * `DELETE /api/v1/shops/{shop_id}/reviews/mine`: Permanently deletes caller's review; permitted even if shop is `PENDING_REVIEW` or `EXCLUDED`.
* **Database Write Privilege Protection & Secure RPCs**:
  * Direct PostgREST `INSERT` and `UPDATE` on `reviews` revoked; writes routed through PostgreSQL `SECURITY DEFINER` RPCs (`create_user_review`, `update_user_review`) with `auth.uid()` derivation and revoked `PUBLIC` execution privileges.
  * Immutable author name snapshotting from user metadata with fallback to `'LOKAL User'`. Never exposes user emails or internal UUIDs in review responses.
  * Strict `source = 'lokal'` filtering across application lookups, updates, and deletes.
* Google Places API (New) integration for transient external review retrieval with provider attribution and source links. No caching or persistence of Google review content.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), external provider failures (`502`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **193 passing tests**, covering auth, shops, curation, nearby discovery, search/filtering/sorting, external reviews, and first-party user reviews.

---

# Current Database & Security Architecture

The database is managed through PostgreSQL in Supabase with Row Level Security (RLS) and controlled stored procedures:

* **Tables**:
  * `shops`: Core coffee shop details (name, address, coordinates, Google Place ID, etc.).
  * `shop_curation`: Business eligibility status (`APPROVED`, `EXCLUDED`, `PENDING_REVIEW`), observed location counts, evidence metadata, and audit logs.
  * `reviews`: Stores first-party LOKAL user reviews and historical/external review metadata.
* **Review Schema & Integrity**:
  * `user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE`
  * `author_name TEXT NOT NULL DEFAULT 'LOKAL User'`
  * `source TEXT NOT NULL DEFAULT 'lokal'`
  * `uq_reviews_user_shop UNIQUE (user_id, shop_id)`: Enforces single review per user per coffee shop.
  * Indexes: `idx_reviews_shop_id` and `idx_reviews_user_id`.
* **Stored Procedures & Privilege Architecture**:
  * `get_nearby_shops`: Defined with `SECURITY INVOKER` in `20260923000000_shop_search_and_filters.sql`. Implements bounding box pruning, Haversine spherical distance calculation, case-insensitive wildcard-escaped search (`ESCAPE E'\\'`), minimum rating filtering against `shops.rating`, and deterministic tie-breaker sorting. Restricted to `shop_curation.status = 'APPROVED'`.
  * `create_user_review(p_shop_id, p_rating, p_content)`: `SECURITY DEFINER` with execution granted strictly to `authenticated` (revoked from `PUBLIC`). Validates rating (1–5), verifies shop existence and `APPROVED` curation status, enforces uniqueness, resolves author display name snapshot from user profile metadata, and inserts review with server timestamps.
  * `update_user_review(p_shop_id, p_rating, p_content, p_update_content)`: `SECURITY DEFINER` with execution granted strictly to `authenticated` (revoked from `PUBLIC`). Enforces field presence, validates rating, verifies shop is `APPROVED`, enforces caller ownership and `source = 'lokal'`, preserves server-managed fields, and updates `rating`, `content`, and `updated_at`.
* **Table Access Privileges**:
  * Direct `INSERT` and `UPDATE` on `reviews` are revoked from `authenticated`, `anon`, and `public`.
  * `SELECT` and `DELETE` are granted to `authenticated`.
* **Row Level Security (RLS) Policies**:
  * `SELECT`: Authenticated users can select reviews for coffee shops with `shop_curation.status = 'APPROVED'` or their own reviews (`auth.uid() = user_id`).
  * `DELETE`: Authenticated users can delete only their own reviews (`auth.uid() = user_id`).
  * Service role maintains administrative access for maintenance tasks.

---

# Current Data / AI Architecture Direction

The project implements a hybrid review-data architecture:

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
       summarization / recommendations
                  ↓
             LOKAL Mobile
```

The external review layer retrieves reviews from Google Places API (New) on demand. External review content is transient and is not persisted or cached in Supabase, preserving provider attribution and policy compliance.

First-party LOKAL reviews are persisted in Supabase with author name snapshotting, rating constraints, single-review uniqueness, and RLS/RPC security.

The review domain merges first-party LOKAL reviews and external reviews into a unified provider-neutral representation (`UnifiedReview`), exposing separate external and community metrics so downstream consumers can clearly distinguish first-party feedback.

The AI layer remains a future consumer of the unified review domain, designed to ingest normalized reviews for summarization and "Must-Try" recommendations without coupling to specific review sources.

Independent-business eligibility and curation are maintained as a separate domain concern, ensuring review operations respect public discovery eligibility rules.

---

# Next Task

The next feature should be defined through the next GitHub Issue after reviewing the completed coffee shop search, filtering, and sorting capabilities alongside the existing unified review domain.

With discovery, search, filtering, sorting, and user reviews operational, the project is positioned to build toward the AI layer (e.g. **AI Review Summaries / Issue #26**) or mobile user authentication integration.

Before implementation:

1. Review the current database schema, discovery RPCs, curation layer, review service, and mobile discovery sheet.
2. Define the product requirement and observable acceptance criteria for the next capability.
3. Review dependencies, latency implications, and external AI provider or auth trade-offs.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

Discovery with debounced search, distance preset filters (1 km, 3 km, 5 km), minimum rating filters (4.0+, 4.5+), and configurable sorting (Nearest vs. Top Rated) is functional across the database RPC, FastAPI backend, and mobile UI. The database stored procedure enforces bounding box pre-filtering, spherical distance calculation, SQL wildcard character escaping, and deterministic tie-breaker sorting under `SECURITY INVOKER` privileges. The unified review domain is functional with separate external and first-party metrics. Note on local QA: local mobile discovery requires a valid Supabase JWT access token passed via `authToken`, pending full mobile authentication UI integration.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **SQL Wildcard Escaping in Pattern Matching**: When implementing SQL `ILIKE` pattern matching with user-supplied search text, wildcard characters (`%`, `_`, `\`) must be escaped before enclosing in `%...%` wildcards, using an explicit escape clause (e.g., `ESCAPE E'\\'`) to prevent unintended pattern broadening.
* **In-Flight Request Lifecycle Invalidation on State Reset**: When a prerequisite dependency (such as user location coordinates) becomes null or invalid, any active in-flight asynchronous request must be invalidated (e.g., via monotonic request ID advancement) prior to clearing local state. Otherwise, a resolving prior request can overwrite the cleared/error state with stale data.
* **Strict API Contract Parameter Normalization**: Query parameters like `sort_by` should enforce strict lowercase matching or reject invalid case variants at the backend boundary (`Query(..., pattern="^(distance|rating)$")`), while client services should explicitly normalize arguments (e.g., `.toLowerCase()`) to ensure robust contract adherence.
* **Client-Side Debouncing with Deterministic Race Handling**: Search inputs should use client-side debouncing (e.g., 350ms) to prevent excessive backend queries during typing, coupled with monotonic request sequence tracking so that out-of-order network responses are safely discarded.
* **Deterministic Multi-Column Ordering (Tie-Breakers)**: When sorting query results by non-unique columns (like `distance_meters` or `rating`), secondary and tertiary tie-breakers (e.g., `ORDER BY distance_meters ASC, id ASC` or `ORDER BY rating DESC NULLS LAST, distance_meters ASC, id ASC`) must be included in database queries to guarantee deterministic pagination and UI stability.
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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #27 and merge of PR #28)
