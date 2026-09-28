# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, independent business eligibility and curation, external review data layer, first-party LOKAL user reviews, mobile user authentication with secure session management, and AI-generated review summaries are established.

The project is now building application-level features that expand LOKAL's AI capabilities, including AI must-try recommendations.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed feature, **AI-Generated Review Summaries (GitHub Issue #31)**, introduces LOKAL's first AI-powered capability: concise, objective synthesized review summaries with highlight chips for approved coffee shops.

Review summaries are powered by the Google Gemini API (`gemini-2.5-flash`) via a clean provider abstraction (`ReviewSummarizer` protocol) and lightweight native HTTP client (`httpx`), avoiding heavy AI frameworks like LangChain or LlamaIndex. Gemini is configured with `thinkingBudget: 0` to preserve the entire output token allowance for structured JSON synthesis, and non-`STOP` completions are rejected. Responses are validated against an application-level Pydantic schema (`ReviewSummaryContent`), failing closed to HTTP 502 Bad Gateway on malformed or schema-nonconforming outputs.

To maintain a zero-cost MVP architecture without Redis or a persistent summary dataset, summaries are cached in an in-memory 1-hour TTL cache (`InMemorySummaryCache`, 500 shops max capacity). A thread-safe, per-shop generation/version mechanism protects against race conditions where in-flight summarization requests could otherwise overwrite recent review mutations with stale pre-mutation summaries. First-party review creation, editing, and deletion immediately invalidate the cache and advance the generation version.

User privacy and prompt-injection safety are strictly enforced: reviews are stripped of reviewer author names, user IDs, review IDs, and visit dates; rating-only reviews are excluded; and remaining reviews are passed inside `<reviews>` tags with explicit anti-override system instructions. Summaries require a minimum threshold of 3 usable reviews with text.

On the mobile client, `ShopDetailCard` renders the AI summary card asynchronously without blocking the shop presentation. It handles loading, available, insufficient reviews (< 3 reviews), and error states with localized retries. Monotonic request counters protect the UI against shop-switching race conditions and out-of-order responses, and review mutations automatically trigger a fresh summary refresh.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #31 — AI-Generated Review Summaries

**Status:** ✅ Completed

### Completed Work

* **Provider Abstraction & Native Gemini Integration**:
  * Implemented `ReviewSummarizer` (Protocol) and `GeminiReviewSummarizer` in `backend/app/services/reviews/summary.py`.
  * Targeted Gemini REST API `v1beta/models/{model}:generateContent` using native `httpx` (no LangChain, LlamaIndex, or heavy AI SDKs).
  * Configurable through `GEMINI_API_KEY` and `GEMINI_MODEL` (default: `gemini-2.5-flash`).
  * Added `"thinkingConfig": {"thinkingBudget": 0}` in `generationConfig` for `gemini-2.5-flash` so internal reasoning tokens do not consume `maxOutputTokens=500`.
  * Enforced completion validation: accepts `finishReason == "STOP"` or absent, rejecting all truncated/safety completions (`MAX_TOKENS`, `SAFETY`, etc.) with `ExternalProviderError`.
  * Fail-closed provider parsing: caught `ValueError`, `TypeError`, `AttributeError`, `KeyError`, and `IndexError` during response JSON extraction, converting malformed structures into `ExternalProviderError` without leaking raw provider bodies in logs.
* **Application-Level Validation Boundary**:
  * Gemini is requested to output structured JSON matching a JSON schema.
  * Implemented `ReviewSummaryContent` Pydantic model (`summary: str`, `positive_themes: list[str]`, `negative_themes: list[str]`).
  * Application strictly validates raw text with `ReviewSummaryContent.model_validate_json()`, mapping any validation or parsing failure to `ExternalProviderError` and HTTP 502 Bad Gateway.
* **Privacy & Prompt Injection Protections**:
  * Strips all reviewer user IDs, author names, review IDs, and visit dates. Only `{"rating": r.rating, "text": r.text}` is sent.
  * Excludes rating-only reviews (empty or whitespace text).
  * Bounds inputs: maximum 10 usable reviews, each truncated to 500 characters.
  * Wraps input inside `<reviews>` XML tags and passes explicit system instructions commanding the model to treat review contents as untrusted data and ignore embedded instructions or prompt overrides.
  * Enforces minimum review threshold: requires at least 3 usable reviews with text, returning `status: "insufficient_reviews"` with empty theme lists and null summary when fewer than 3 reviews are available.
* **Generation-Guarded In-Memory Caching**:
  * Implemented `InMemorySummaryCache` with 1-hour TTL (`ttl_seconds=3600.0`) and 500-shop capacity limit with oldest-entry eviction.
  * Guarded with `threading.Lock()` and dual versioning (`_epoch`, `_versions`).
  * `get_shop_summary` captures `generation = cache.get_generation(shop_id)` prior to review fetching and Gemini summarization.
  * Stores via `cache.set_if_generation(..., generation)` atomically verifying the generation has not changed.
  * Prevents race conditions where an in-flight read could overwrite a cache invalidation triggered by a concurrent user review mutation.
  * Hooked immediate cache invalidation and generation advancement into `ReviewService.create_user_review`, `update_user_review`, and `delete_user_review`.
* **API Endpoint & Curation Protection**:
  * Added `GET /api/v1/shops/{shop_id}/reviews/summary` in `backend/app/api/v1/endpoints/reviews.py`.
  * Enforced authentication via `get_current_user`.
  * Enforced fail-closed curation: returns `404 Not Found` if the shop is `PENDING_REVIEW` or `EXCLUDED`.
  * Returns `503 Service Unavailable` if `GEMINI_API_KEY` is unconfigured.
  * Returns `502 Bad Gateway` if Gemini fails, times out, or returns invalid schema data.
* **Non-Blocking Mobile Experience**:
  * Added `fetchShopReviewSummary(shopId, authToken)` in `mobile/src/services/reviewService.ts`.
  * Integrated AI review summary card in `mobile/src/components/ShopDetailCard.tsx`.
  * Loads summary asynchronously in the background after shop details are visible without blocking navigation or reviews.
  * Renders loading spinner, available state with summary paragraph and chips for positive and negative themes, empty/insufficient reviews card, and error state with localized retry button.
  * Monotonic request counter (`currentSummaryRequestId`) discards out-of-order responses and prevents stale data from overwriting active state when switching shops.
  * Automatically refetches summary after user review creation, editing, or deletion.
* **Automated Verification**:
  * Backend regression suite: **229 tests passing** in 1.6s (`python -m unittest discover -s backend/tests`).
  * Mobile test suite: **71 tests passing** in 348ms (`npm test --prefix mobile`).
  * Mobile TypeScript verification: **0 errors** (`npx tsc --noEmit`).
  * Deterministic race testing: verified shop-switching and failed stale responses using controlled promises.
* **Pull Request**:
  * Pull Request #32 was reviewed by CodeRabbit, actionable findings were resolved iteratively (fail-closed parsing, non-STOP rejection, thinking token budget configuration, cache generation tracking, and deterministic race tests), and the PR was approved and merged into `main` by the Product Owner (commit `af26f0df`).

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
| Issue #31 — AI-Generated Review Summaries        | ✅ Complete |
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
  * Automatic Bearer token propagation across nearby coffee shop searches, review operations, and AI summary requests.
* **AI-Generated Review Summaries**:
  * Non-blocking AI review summary card within `ShopDetailCard`.
  * Asynchronous background fetching initiated after shop selection, leaving the rest of the detail card responsive.
  * Concise overall synthesis paragraph summarizing customer sentiment and opinions.
  * Visual highlight chips distinguishing positive highlights and areas to note (negative themes).
  * Graceful insufficient reviews state informing the user when fewer than 3 usable reviews exist.
  * Error state presentation with localized retry action.
  * Monotonic request counter (`currentSummaryRequestId`) preventing stale out-of-order responses from overwriting active state when switching shops.
  * Automatic summary refresh triggered immediately after user review creation, editing, or deletion.
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
  * Monotonic request counter (`currentRequestId`), mutation counter (`currentMutationId`), and summary request counter (`currentSummaryRequestId`) in `ShopDetailCard` ensuring late-arriving responses or mutations from previously selected shops or previous auth sessions are discarded.
  * Component lifecycle keying in `NearbyShopsSheet` (`${selectedShop.id}:${authToken || 'anon'}`) ensuring complete reset of review form, submission, deletion, and summary states on shop selection change.
* Non-blocking review loading and retry behavior.
* Zero external UI dependencies, maintaining scope discipline and clean architecture.

Must-Try recommendations and background location tracking remain outside the current implementation scope.

---

# Current Backend Capabilities

The FastAPI backend currently provides:

* Application configuration through environment variables (including `GEMINI_API_KEY` and `GEMINI_MODEL`).
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
* **AI Review Summarization Layer & Endpoint**:
  * `GET /api/v1/shops/{shop_id}/reviews/summary`: Protected endpoint returning structured AI review summary for an approved coffee shop.
  * `ReviewSummarizer` (Protocol) abstraction enabling clean decoupling from specific AI vendors.
  * `GeminiReviewSummarizer` implementation targeting Google Gemini REST API (`gemini-2.5-flash`) via `httpx`, with `thinkingBudget: 0` to preserve the output token budget for JSON synthesis.
  * Application-level Pydantic schema validation boundary (`ReviewSummaryContent`), failing closed on malformed output or non-`STOP` finish reasons.
  * Privacy-preserving review sanitization: strips author names and internal IDs, passes only rating and truncated text within `<reviews>` XML tags with anti-prompt-injection system instructions.
  * 3-review minimum usable text threshold check; excludes rating-only reviews.
  * `InMemorySummaryCache` (1-hour TTL, 500 capacity) with thread-safe per-shop generation tracking preventing in-flight stale cache repopulation.
  * Automatic cache invalidation and generation advancement on first-party review creation, editing, and deletion.
* **Database Write Privilege Protection & Secure RPCs**:
  * Direct PostgREST `INSERT` and `UPDATE` on `reviews` revoked; writes routed through PostgreSQL `SECURITY DEFINER` RPCs (`create_user_review`, `update_user_review`) with `auth.uid()` derivation and revoked `PUBLIC` execution privileges.
  * Immutable author name snapshotting from user metadata with fallback to `'LOKAL User'`. Never exposes user emails or internal UUIDs in review responses.
  * Strict `source = 'lokal'` filtering across application lookups, updates, and deletes.
* Google Places API (New) integration for transient external review retrieval with provider attribution and source links. No caching or persistence of Google review content.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), external provider failures (`502`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **229 passing tests**, covering auth, shops, curation, nearby discovery, external reviews, first-party user reviews, and AI review summaries.

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

The project implements a hybrid review-data architecture with operational AI review summarization:

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
     (ReviewSummaryService / Gemini)
                  ↓
             LOKAL Mobile
```

The external review layer retrieves reviews from Google Places API (New) on demand. External review content is transient and is not persisted or cached in Supabase, preserving provider attribution and policy compliance.

First-party LOKAL reviews are persisted in Supabase with author name snapshotting, rating constraints, single-review uniqueness, and RLS/RPC security.

The review domain merges first-party LOKAL reviews and external reviews into a unified provider-neutral representation (`UnifiedReview`), exposing separate external and community metrics so downstream consumers can clearly distinguish first-party feedback.

The AI layer ingests sanitized reviews from the unified review domain to generate structured review summaries (`ReviewSummaryService`), using `GeminiReviewSummarizer` via HTTP requests to Google Gemini API. Summaries are cached in-memory with a 1-hour TTL and generation-guarded invalidation, without creating a persistent summary database table.

Independent-business eligibility and curation are maintained as a separate domain concern, ensuring review and AI summary operations respect public discovery eligibility rules (`APPROVED` required).

---

# Next Task

The next feature should be defined through the next GitHub Issue after reviewing the completed AI review summaries architecture and current application state.

With user authentication, unified reviews, and AI review summarization active, the logical next capability is **AI Must-Try Recommendations** (menu and beverage recommendations derived from review insights) or another feature prioritized by the Product Owner.

Before implementation:

1. Review the current database schema, curation layer, review service, AI summarizer, and mobile cards.
2. Define the product requirement and observable acceptance criteria for the next capability.
3. Review dependencies, latency implications, and external AI provider trade-offs.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

The unified review domain and AI review summarization are operational. External reviews remain transient and compliant with provider policies, while first-party reviews are securely persisted in Supabase. In-memory summary caching with generation versioning is active. Mobile user authentication, review mutations, and non-blocking summary cards are operational and fully tested.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **Generation-Guarded In-Memory Caching**: When caching asynchronous LLM responses in memory without a persistent database, protect the cache with an atomic generation/version check. Long-running in-flight summarization requests must not write back stale pre-mutation summaries if an invalidation occurred while the request was in flight.
* **Application-Level Validation Boundary for LLM Outputs**: Never rely solely on vendor "structured output" flags or schema requests. Always validate the returned content with Pydantic (`ReviewSummaryContent.model_validate_json`) and fail closed to HTTP 502 Bad Gateway if the model returns malformed, incomplete, or schema-nonconforming responses.
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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #31 and merge of PR #32)
