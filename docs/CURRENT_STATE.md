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

The core application stack is operational. The latest completed feature, **LOKAL User Reviews (GitHub Issue #24)**, establishes a secure, first-party review system integrated into the unified review domain alongside transient external reviews.

Authenticated users can submit, view, edit, and delete their own reviews for approved independent coffee shops. Review updates are strictly scoped to first-party LOKAL records (`source = 'lokal'`), ratings are constrained to 1–5 stars, review text is optional up to 1000 characters, and each user is limited to a single review per coffee shop. Direct database writes via PostgREST are blocked in favor of controlled PostgreSQL `SECURITY DEFINER` RPC functions with revoked `PUBLIC` execution privileges, protecting server-managed fields (`user_id`, `author_name`, `source`, `created_at`, `updated_at`). Curation rules ensure reviews cannot be created or edited for shops that are not approved for public discovery, while users retain the ability to inspect or delete their existing reviews even if a shop becomes excluded.

In the mobile app, users can view first-party reviews alongside external reviews with separate rating metrics (preserving external provider attribution and first-party LOKAL community scores), view and manage their own review via an interactive modal composer, and experience robust protection against stale asynchronous responses and mutation races across shop selections.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #24 — LOKAL User Reviews

**Status:** ✅ Completed

### Completed Work

* **Database Schema & Constraints**:
  * Enhanced the `reviews` table with `user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE`, `author_name TEXT NOT NULL DEFAULT 'LOKAL User'`, and default `source = 'lokal'`.
  * Added unique constraint `uq_reviews_user_shop` on `(user_id, shop_id)` enforcing a strict one-review-per-user-per-shop limit at the database level.
  * Added performance and lookup indexes `idx_reviews_shop_id` and `idx_reviews_user_id`.
* **Database Privilege Hardening & Secure RPCs**:
  * Revoked direct table `INSERT` and `UPDATE` privileges on `reviews` from `authenticated`, `anon`, and `public` roles, requiring all write mutations to pass through controlled PostgreSQL `SECURITY DEFINER` stored procedures.
  * Implemented `create_user_review(p_shop_id, p_rating, p_content)`: derives caller identity from `auth.uid()`, enforces 1–5 integer rating, validates shop existence and `APPROVED` curation status, enforces single review per shop, resolves author display name snapshot from user profile metadata (`full_name` or `display_name`, falling back to `'LOKAL User'`), and stamps server-managed timestamps (`created_at`, `updated_at`).
  * Implemented `update_user_review(p_shop_id, p_rating, p_content, p_update_content)`: derives caller identity from `auth.uid()`, enforces field-presence semantics, validates 1–5 integer rating when present, validates shop existence and `APPROVED` curation status, enforces ownership and `source = 'lokal'` filtering, preserves server-managed fields (`author_name`, `source`, `user_id`, `shop_id`, `created_at`), atomically updates rating and/or content, and advances `updated_at`.
  * Explicitly revoked `EXECUTE` on both review RPCs from `PUBLIC` and granted execution strictly to `authenticated`.
* **Row Level Security (RLS)**:
  * Configured `SELECT` policy restricting review read access to reviews of `APPROVED` shops (`shop_curation.status = 'APPROVED'`) or the authenticated caller's own review (`auth.uid() = user_id`).
  * Configured `DELETE` policy allowing authenticated users to delete their own review (`auth.uid() = user_id`) even if the shop is excluded or pending review.
* **Backend API Endpoints**:
  * `POST /api/v1/shops/{shop_id}/reviews`: Submits a first-party LOKAL review for an approved coffee shop (201 Created).
  * `GET /api/v1/shops/{shop_id}/reviews/mine`: Retrieves the authenticated caller's own review (200 OK or 404 Not Found); permitted even if the shop is currently excluded or pending review.
  * `PATCH /api/v1/shops/{shop_id}/reviews/mine`: Partially updates the caller's review with field-presence semantics (200 OK); blocked if the shop is not approved.
  * `DELETE /api/v1/shops/{shop_id}/reviews/mine`: Permanently deletes the caller's review (200 OK); permitted even if the shop is currently excluded or pending review.
  * `GET /api/v1/shops/{shop_id}/reviews`: Retrieves unified reviews combining first-party LOKAL reviews and transient external Google reviews; returns 404 Not Found if the shop is pending review or excluded.
* **Review Domain Modeling & Separation of Metrics**:
  * Preserved separate rating metrics in `ShopReviewsResponse`: `average_rating` and `total_reviews_count` reflect external Google Places provider data, while `lokal_average_rating` and `lokal_reviews_count` reflect first-party community reviews (no blending into a composite score).
  * Domain model `UnifiedReview` includes `is_edited` (derived deterministically from `created_at != updated_at`), `published_at`, `updated_at`, `author` (`display_name`, `avatar_url`, `profile_url`), and provider attribution.
  * Enforced strict `source = 'lokal'` isolation in both application lookups and database RPCs to prevent unintentional modification of non-LOKAL rows.
  * External Google review content remains transient (unpersisted in Supabase).
* **Mobile Application Integration**:
  * Displayed first-party LOKAL reviews alongside external reviews with separate rating sections ("LOKAL Community" rating and count alongside Google rating).
  * Prominently presented the authenticated user's own review with dedicated Edit and Delete options.
  * Added an interactive inline review composer modal supporting star rating selection (1–5), optional review text with character count (max 1000 characters), and validation feedback.
  * Implemented stale async request and mutation protection using monotonic request (`currentRequestId`) and mutation (`currentMutationId`) sequence counters in `ShopDetailCard`, discarding out-of-order responses.
  * Added compound component keying in `NearbyShopsSheet` (`${selectedShop.id}:${authToken || 'anon'}`) to reset review form and mutation states cleanly whenever the selected shop or auth token changes.
* **Automated Verification**:
  * Completed backend verification with **182 unit/regression tests passing** in 1.3s (including 35 dedicated first-party user review tests and 22 review data layer tests).
  * Completed mobile verification with **26 automated tests passing** in 260ms (including 11 `reviewService` tests, 5 `shopReviewState` async race tests, and 10 `shopService` tests).
  * Completed TypeScript verification with **0 errors** (`npx tsc --noEmit`).
  * *Verification environment distinction*: Automated tests in the repository validate application logic, HTTP contracts, and SQL RPC generation through mock harnesses. Live PostgreSQL constraints, RLS policy enforcement, and database triggers apply upon migration deployment to Supabase.
* **Pull Request**:
  * Pull Request #25 was evaluated by CodeRabbit, actionable findings were resolved, and the PR was approved and merged into `main` by the Product Owner (commit `1bc393c4`).

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
  * `20260919000000_user_reviews.sql`: First-party user reviews schema, constraints, RLS policies, table privilege hardening, and secure write RPCs.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Authenticated coffee shop management via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`).
* Authenticated nearby coffee shop discovery via `GET /api/v1/shops/nearby`.
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
* Automated backend regression testing with **182 passing tests**, covering auth, shops, curation, nearby discovery, external reviews, and first-party user reviews.

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
* **Table Access Privileges**:
  * Direct `INSERT` and `UPDATE` on `reviews` are revoked from `authenticated`, `anon`, and `public`.
  * `SELECT` and `DELETE` are granted to `authenticated`.
* **Controlled Security Definer RPCs**:
  * `create_user_review(p_shop_id, p_rating, p_content)`: Validates rating (1–5), verifies shop existence and `APPROVED` curation status, enforces uniqueness, resolves author display name snapshot from user profile metadata, and inserts review with server timestamps.
  * `update_user_review(p_shop_id, p_rating, p_content, p_update_content)`: Enforces field presence, validates rating, verifies shop is `APPROVED`, enforces caller ownership and `source = 'lokal'`, preserves server-managed fields, and updates `rating`, `content`, and `updated_at`.
  * Stored procedure execution privileges are revoked from `PUBLIC` and granted strictly to `authenticated`.
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

The next feature should be defined through the next GitHub Issue after reviewing the completed first-party review architecture and current application state.

With the unified review domain now active with both first-party and external reviews, the project is ready to build toward the AI layer (e.g. **AI Review Summaries / Issue #26**).

Before implementation:

1. Review the current database schema, curation layer, review service, and mobile review presentation.
2. Define the product requirement and observable acceptance criteria for the next capability.
3. Review dependencies, latency implications, and external AI provider trade-offs.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

The unified review domain is functional with separate external and first-party metrics. External reviews remain transient and compliant with provider policies, while first-party reviews are securely persisted in Supabase. AI processing of unified review content remains a planned next step.

---

# Session Learnings

The recent development cycles established the following engineering practices:

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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #24 and merge of PR #25)
