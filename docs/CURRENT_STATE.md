# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, independent business eligibility and curation, external review data layer, first-party LOKAL user reviews, and mobile user authentication with secure session management are established.

The project is now building application-level features that provide the foundation for LOKAL's future AI capabilities, including AI review summaries and recommendations.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed feature, **Mobile User Authentication & Session Management (GitHub Issue #29)**, establishes a secure, client-side authentication and session lifecycle management system for the React Native (Expo) mobile application.

Users can securely register and log in using email and password, authenticate against the FastAPI backend, and store JWT credentials in hardware-backed secure storage via `expo-secure-store`. Credential storage strictly enforces fail-fast security in production and native environments by forbidding silent downgrades to in-memory storage. On application launch, sessions are automatically restored with profile verification against `GET /api/v1/auth/me`. The authentication state machine (`AuthContext`) strictly differentiates between permanently invalid sessions (`401 Unauthorized`, which automatically deletes stored credentials and transitions to unauthenticated) and transient network or server errors (5xx/timeouts, which preserves the stored credential and presents an actionable recovery card with both Retry and Sign Out options).

Monotonic operation generation guards (`operationGenerationRef`) protect the entire authentication lifecycle against race conditions and out-of-order asynchronous responses (such as concurrent logins, retries while awaiting restoration, or retries triggered while logout is in progress). Sign out is fail-safe, ensuring local credentials are deleted regardless of backend network availability, and trailing retries are immediately invalidated. Authenticated API requests across the mobile app (including nearby shop search and review operations) automatically attach the active Bearer token.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #29 — Mobile User Authentication & Session Management

**Status:** ✅ Completed

### Completed Work

* **Hardware-Backed Secure Token Storage**:
  * Implemented `mobile/src/services/secureStorage.ts` wrapping `expo-secure-store` with key `lokal_access_token`.
  * Enforced production security invariant: in-memory storage adapter is restricted exclusively to headless Node.js test environments; native or production runtimes fail fast with explicit errors if SecureStore is unavailable rather than silently downgrading credential security.
  * Enforced token validation: rejects empty or whitespace-only strings before storage.
* **Authentication Service**:
  * Implemented `mobile/src/services/authService.ts` providing typed client wrappers for backend auth endpoints:
    * `login({ email, password })`: `POST /api/v1/auth/login`
    * `register({ email, password })`: `POST /api/v1/auth/register`
    * `logout(token)`: `POST /api/v1/auth/logout` (Bearer authenticated)
    * `getMe(token)`: `GET /api/v1/auth/me` (Bearer authenticated)
  * Integrated fixed request timeouts (10,000ms) across all authentication requests using `AbortController` to guarantee stalled requests do not leave the client hanging in transient states.
  * Structured domain error handling: mapped HTTP errors into strongly typed `AuthError` instances with status codes and backend detail messages.
* **Session Lifecycle & State Machine**:
  * Implemented `mobile/src/context/AuthContext.ts` providing `AuthProvider` and `useAuth()` hook managing session state (`restoring`, `authenticated`, `unauthenticated`).
  * Built using pure TypeScript and `React.createElement` to ensure seamless native execution and direct headless Node.js test execution.
  * **Automatic Session Restoration**:
    * Automatically attempts session restoration from SecureStore on initial app mount.
    * If no token is stored, transitions directly to `unauthenticated`.
    * If a token is stored, verifies it against `GET /api/v1/auth/me`. On success, transitions to `authenticated` with user profile.
    * On `401 Unauthorized`, treats token as expired/revoked, purges SecureStore, and transitions to `unauthenticated`.
    * On network or 5xx server failure, preserves the stored token and sets `status: 'restoring'` with an actionable `restorationError` message.
  * **Fail-Safe Logout**:
    * Calls `POST /api/v1/auth/logout` using the active token.
    * Guarantees local credential deletion and transition to `unauthenticated` inside a `finally` block, ensuring network or backend failures never trap the user in an authenticated local state.
  * **Generation Guards Against Stale/Concurrent Operations**:
    * Protected state transitions using a monotonic provider-level generation counter (`operationGenerationRef`).
    * Invalidates pending restoration tasks whenever login, registration, or logout begins.
    * Increments the generation counter in the `logout()` `finally` block immediately after local credential deletion, ensuring retries initiated while logout was awaiting network response or cleanup cannot overwrite the unauthenticated state or re-introduce a session.
* **Authentication UI & User Experience**:
  * Implemented `mobile/src/screens/LoginView.tsx` with email and password inputs, form validation, loading indicators, error banner presentation, and navigation toggle to registration.
  * Implemented `mobile/src/screens/RegisterView.tsx` with email, password, and confirmation password inputs, password match validation, loading indicators, error banner presentation, and navigation toggle to login.
  * Added a dedicated restoration error recovery view in `mobile/App.tsx` displaying the failure message alongside both **Retry** and **Sign Out** actions.
* **API Integration & Bearer Token Propagation**:
  * Updated `mobile/src/services/shopService.ts` and `mobile/src/services/reviewService.ts` to consume the active auth token from `AuthContext` and attach it as `Authorization: Bearer <token>` for authenticated requests.
* **Automated Verification**:
  * Completed mobile verification with **60 automated tests passing** in 281ms:
    * 12 tests in `authService.test.mjs` (endpoints, payload structures, 401 handling, timeout handling).
    * 16 tests in `authState.test.mjs` (SecureStore security, in-memory isolation, restoration transitions, 401 token purge, network failure retry, explicit sign out during restoration failure, race condition regression tests).
    * 16 tests in `reviewService.test.mjs` (CRUD operations, error formatting, race guards, token change resets).
    * 16 tests in `shopService.test.mjs` (query params, formatting, nearby search, Bearer token integration).
  * Completed mobile TypeScript verification with **0 errors** (`npx tsc --noEmit`).
  * Completed backend regression verification with **193 tests passing** in 1.2s (`python -m unittest discover -s backend/tests`).
* **Pull Request**:
  * Pull Request #30 was evaluated by CodeRabbit, actionable findings (request timeouts, secure storage downgrade prevention, generation race protection, explicit sign-out during restoration error, and deterministic race tests) were resolved iteratively, and the PR was approved and merged into `main` by the Product Owner (commit `6af27d73`).

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
| Issue #29 — Mobile User Authentication & Session Management | ✅ Complete |
| AI-Assisted Engineering Workflow                 | ✅ Complete |
| AI Review Summaries                              | ⏳ Planned  |
| AI Must-Try Recommendations                      | ⏳ Planned  |

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
  * Automatic Bearer token propagation across nearby coffee shop searches and user review submissions.
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

The next feature should be defined through the next GitHub Issue after reviewing the completed mobile authentication architecture and current application state.

With the unified review domain active with both first-party and external reviews and the mobile client providing full user authentication and session management, the project is ready to build toward the AI layer (e.g. **AI Review Summaries / Issue #26**).

Before implementation:

1. Review the current database schema, curation layer, review service, and mobile review presentation.
2. Define the product requirement and observable acceptance criteria for the next capability.
3. Review dependencies, latency implications, and external AI provider trade-offs.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

The unified review domain is functional with separate external and first-party metrics. External reviews remain transient and compliant with provider policies, while first-party reviews are securely persisted in Supabase. Mobile user authentication and session persistence are operational and tested. AI processing of unified review content remains the planned next step.

---

# Session Learnings

The recent development cycles established the following engineering practices:

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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #29 and merge of PR #30)
