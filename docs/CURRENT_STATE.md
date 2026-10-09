# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 3 — MVP Polish & Validation**

The project bootstrapping and core application feature phases are complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, independent business eligibility and curation, external review data layer, first-party LOKAL user reviews, mobile user authentication with secure session management, AI-generated review summaries, AI-generated "Must Try" recommendations, favorite coffee shops, the user favorites list / profile discovery flow, advanced shop search and filtering, personalized coffee shop recommendations, coffee shop owner claiming and dashboard, and community feed and social sharing are established.

The original LOKAL MVP objective is now functionally covered: **locate local independent coffee shops and help users quickly understand each shop through AI-generated review summaries**.

The project is now focused on validating and polishing that MVP rather than expanding the feature surface by default. Current work should prioritize **UI/UX refinement**, **populating the database with realistic data**, and **end-to-end testing against that data** so the core discovery and AI-summary experience can be evaluated as a real product.

Features such as coffee shop menus and photo galleries remain future exploration candidates and are not required for the current MVP definition.

# Current Status

🟢 **On Track**

The core application stack is operational. **Community Feed & Social Sharing (GitHub Issue #47)** is the latest completed feature and marks the completion of the currently planned core application feature expansion.

The original LOKAL MVP is centered on a simple product loop: **locate local independent coffee shops and quickly understand each shop through AI-generated review summaries**. The application already provides the underlying discovery, curation, review-data, shop-detail, and AI-summary capabilities needed for that loop.

The current phase is therefore focused on **MVP Polish & Validation** rather than automatically adding more product features. The immediate priorities are:
* **UI/UX refinement** across the core discovery and shop-understanding experience.
* **Realistic database population** with enough varied shop and review data to exercise the application meaningfully.
* **End-to-end validation** of the MVP using that realistic data, including discovery, shop details, review data, and AI-generated summaries.

The goal of this phase is to determine whether the existing MVP experience is polished, coherent, reliable, and useful with realistic data. **Coffee shop menus and photo galleries remain future exploration candidates and are not required to satisfy the current MVP definition.**

The latest merged implementation is verified through **404 passing backend tests**, **209 passing mobile tests**, **109 passing database pgTAP assertions**, and **0 TypeScript compilation errors**.

The engineering workflow remains formalized under the **AI-Assisted Engineering Workflow**.

The next work cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

# Latest Completed Feature

## GitHub Issue #47 — Community Feed and Social Sharing

**Status:** ✅ Completed

### Completed Work

* **Database Schema, Migrations, & Stored Procedures (`supabase/migrations/20261007000000_community_feed.sql`)**:
  * Created partial chronological index `idx_reviews_community_feed ON reviews (created_at DESC, id DESC) WHERE source = 'lokal'` optimizing community feed lookups.
  * Implemented community feed stored procedure `get_community_feed(p_limit, p_offset)`:
    * Declared `SECURITY DEFINER STABLE` with `SET search_path = public, pg_temp`.
    * Enforces inner joins on `shops` and `shop_curation` strictly requiring `status = 'APPROVED'`.
    * Guarantees deterministic chronological ordering: `ORDER BY r.created_at DESC, r.id DESC`.
    * Projects privacy-safe review and shop fields: `id`, `shop_id`, `shop_name`, `shop_address`, `rating`, `content`, `author_name`, `created_at`, `updated_at`. Permitted IDs (`review.id` and `shop_id`) allow client-side keying and navigation, while strictly excluding sensitive user identifiers (`user_id`, emails, claim info, and curator notes).
    * Implemented bounded pagination: clamps limit between 1 and 50 (default 20), fetches `limit + 1` rows internally, and returns at most `limit + 1` rows to enable authoritative backend derivation of `has_more`.
    * Revoked execution permissions from `PUBLIC` and `anon`; granted strictly to `authenticated` and `service_role`.
  * Created comprehensive pgTAP test suite `supabase/tests/04_community_feed.sql` containing **12 assertions** covering execution permissions, deterministic ordering, limit + 1 extra row behavior, offset paging, curation filtering, source isolation (`source = 'lokal'`), dynamic curation demotion, review updates and deletions, and privacy projection.
* **Backend Community Service & Endpoints (FastAPI)**:
  * Implemented `GET /api/v1/community/feed` endpoint in `backend/app/api/v1/endpoints/community.py`:
    * Protected by `get_current_user` and `get_authenticated_supabase`.
    * Query parameters: `limit` (default 20, `ge=1, le=50`) and `offset` (default 0, `ge=0`).
    * Mounted on API v1 router under `/community` with tag `["Community"]`.
  * Implemented `CommunityService` in `backend/app/services/community.py`:
    * Enforces bounded limit clamping (`1 <= limit <= 50`).
    * Invokes `get_community_feed` RPC via authenticated Supabase client.
    * Derives authoritative `has_more = len(raw_items) > limit`.
    * Slices items to `raw_items[:limit]`, returning at most the requested limit.
    * Sanitizes database exceptions into HTTP 500 without leaking internal database errors.
  * Defined Pydantic schemas in `backend/app/schemas/community.py`:
    * `CommunityFeedItem`: permitted navigation IDs (`id`, `shop_id`), shop metadata, rating, content, author display name, timestamps, and computed `is_edited` field (`bool(updated_at and updated_at != created_at)`).
    * `CommunityFeedResponse`: `items: list[CommunityFeedItem]` and `has_more: bool`.
  * Added 9 comprehensive backend regression tests in `backend/tests/test_community_feed.py`, bringing the total backend suite to **404 passing tests**.
* **Mobile Community Feed Experience & Social Sharing (React Native + Expo)**:
  * Added top-left `👥 Community` button on `LokalMapView` (`top: 50, left: 16`), mirroring the top-right `Profile` button.
  * Implemented modal feed view `CommunityFeedView.tsx` with `presentationStyle="pageSheet"`:
    * Displays chronological cards with star ratings, author display names, relative timestamps, and review excerpts.
    * Full asynchronous lifecycle handling: loading indicator, empty state, localized error banner with retry action, pull-to-refresh spinner, and infinite scroll footer spinner.
    * Inline navigation: "View Shop" opens `ShopDetailCard` with a `< Back to Community` action, seamlessly preserving underlying feed state.
    * Monotonic request guard: `shopRequestIdRef = useRef(0)` invalidating in-flight shop fetches on rapid re-selection and incremented on modal dismissal (`!visible || !authToken`) to prevent late responses from repopulating state after close.
  * Implemented pure request coordinator `CommunityFeedController` in `mobile/src/hooks/useCommunityFeed.ts`:
    * Monotonic request sequence tracking (`requestId`) discarding out-of-order responses.
    * Infinite scroll `loadMore` with existing ID deduplication and pagination bounds.
    * Strict principal isolation: immediately clears `items` and resets `hasMore` to `false` when principal changes in `loadInitial` and `refresh`, ensuring failed requests never restore previous principal data.
    * Prevents pagination deadlocks: clears `isLoadingMore = false` in `refresh()` catch block.
    * Active cancellation: `cancel()` increments `requestId` and immediately clears `isLoading`, `isLoadingMore`, and `isRefreshing`.
  * Implemented native social sharing utilities in `mobile/src/services/communityService.ts`:
    * `shareCommunityReview`: formats clean plain-text share message with LOKAL branding, shop name, star rating, author attribution, and bounded review excerpt ($\le 180$ characters with ellipsis). Contains zero internal IDs.
    * `shareShop`: formats clean plain-text share message with shop name, address, and rating.
    * Integrated native `Share` action button in `ShopDetailCard` header.
    * Graceful error and cancellation handling avoiding UI crashes across platforms.
  * Added mobile unit tests in `mobile/tests/communityService.test.mjs` (10 tests), `mobile/tests/communityFeedController.test.mjs` (15 tests), and `mobile/tests/communityFeedShopSelection.test.mjs` (5 tests), bringing the mobile test suite to **209 passing tests**.
* **Automated Verification**:
  * Database pgTAP test suite: **109 / 109 assertions passed** across 4 suites (`supabase test db`).
  * Backend regression suite: **404 / 404 tests passed** (`./backend/.venv/bin/python -m unittest discover -s backend/tests -v`).
  * Mobile test suite: **209 / 209 tests passed** (`npm test --prefix mobile`).
  * Mobile TypeScript compiler: **0 errors** (`./mobile/node_modules/.bin/tsc --noEmit --project mobile/tsconfig.json`).
* **Pull Request**:
  * Pull Request #48 reviewed by CodeRabbit, all actionable findings resolved (monotonic shop-selection race protection, refresh error pagination unblocking, cancel loading flag reset, and principal-switch refresh isolation), approved, and merged into `main` by the Product Owner (merge commit `c474dbaf`).

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
| Issue #39 — User Favorites List & Profile Discovery          | ✅ Complete |
| Issue #41 — Advanced Shop Search and Filtering               | ✅ Complete |
| Issue #43 — Personalized Coffee Shop Recommendations         | ✅ Complete |
| Issue #45 — Coffee Shop Owner Claiming and Dashboard         | ✅ Complete |
| Issue #47 — Community Feed and Social Sharing                | ✅ Complete |

---

# Current Mobile Capabilities

The React Native (Expo) mobile application currently provides:

* **Community Feed & Social Sharing**:
  * Top-left `👥 Community` button on `LokalMapView` (`top: 50, left: 16`) providing immediate, accessible discovery of community activity, mirroring the top-right `Profile` button.
  * Controlled modal feed presentation (`CommunityFeedView`) using iOS `pageSheet` presentation style.
  * Chronological first-party review cards featuring shop name, shop street address, star ratings, author display names, relative timestamps, `(Edited)` indicators, and review text.
  * Interactive card actions:
    * "View Shop" navigates directly to the inline `ShopDetailCard` with a `< Back to Community` action, preserving feed scroll position and cached items.
    * "Share" invokes native platform sharing with a LOKAL-branded message, star rating, author attribution, and bounded review excerpt ($\le 180$ characters with ellipsis).
  * Native shop sharing via `ShopDetailCard` header action, sharing shop name, street address, and rating.
  * Strict privacy boundary: shared text contains zero internal entity UUIDs or private account information.
  * Complete feed lifecycle states: loading indicator, empty state, localized error presentation with retry button, pull-to-refresh spinner, and infinite scroll pagination footer.
  * Monotonic request guard `shopRequestIdRef` in `CommunityFeedView` preventing race conditions where older shop fetches overwrite newer selections or repopulate `selectedShop` after modal dismissal.
  * Pure request sequencer `CommunityFeedController` (`mobile/src/hooks/useCommunityFeed.ts`):
    * Monotonic request sequence tracking (`requestId`) discarding out-of-order stale responses.
    * Infinite scroll `loadMore` with client-side ID deduplication against existing items.
    * Immediate account isolation: immediately clears `items` and resets `hasMore` to `false` when principal changes in `loadInitial` and `refresh`, ensuring failed requests never restore previous principal data.
    * Resilient pagination unblocking: clears `isLoadingMore = false` in `refresh()` catch block.
    * Active cancellation: `cancel()` increments `requestId` and immediately resets `isLoading`, `isLoadingMore`, and `isRefreshing`.
* **User Profile & Saved Coffee Shops (Favorites Discovery)**:
  * Top-right `Profile` button on the interactive map opening a controlled `ProfileView` modal for authenticated users.
  * User profile header displaying avatar initial, full name or display name fallback (`getUserDisplayName`), email, and an accessible Log Out action.
  * Dedicated saved coffee shops list displaying favorited shops ordered by most-recently favorited first.
  * Complete lifecycle states: loading indicator, error banner with localized retry action, empty state with guidance to save shops, and card list presentation.
  * Shop cards displaying shop name, address, rating, distance, and favorite indicator.
  * Haversine distance calculation from device coordinates when available; defaults to `Number.NaN` and cleanly omits the distance badge when location is unavailable, avoiding false `"0 m"` badges.
  * Controlled navigation flow: Map $\to$ Profile $\to$ Favorites $\to$ Shop Detail $\to$ Favorites $\to$ Profile $\to$ Map, preserving underlying map and return targets.
  * Immediate optimistic UI removal on unfavorite with authoritative refetching on all favorite mutations.
  * Stale favorite mutation protection: `ShopDetailCard` success callbacks verify `currentFavoriteMutationId` ownership before updating parent state.
  * Principal-bound instance lifecycle (`getProfilePrincipalKey`) ensuring account switches cleanly remount the profile view and clear selected shops, while same-account token refreshes preserve instance stability.
  * Pure request sequencer `FavoritesController` providing monotonic request IDs, immediate cache clearing on principal switch, late response discarding, and isolation on replacement fetch failures.
* **Coffee Shop Owner Claiming & Dashboard Experience**:
  * Interactive "Claim This Shop" modal flow (`ClaimShopModal`) accessible from `ShopDetailCard` for authenticated users.
  * Form inputs for Claimant Name, Contact Phone, Role, and Business Proof (e.g. DTI / BIR registration) with client validation and submission error handling.
  * Reactive shop claim status badges displayed on `ShopDetailCard`: `Pending Review` (amber) with explanatory guidance; `Claim Rejected` (red) with curator-provided `rejection_reason`; and `Claim Revoked` (gray).
  * Pure request coordinator `ShopClaimController` (`mobile/src/hooks/useShopClaim.ts`) managing monotonic request sequencing, listener subscriptions, and stale-response cancellation across shop selections and authentication transitions.
  * Segmented control `[Favorites | My Claims]` within `ProfileView` enabling authenticated users to toggle between saved favorite coffee shops and their submitted ownership claims.
  * My Claims tab rendering user's submitted claims with status badges, submission timestamps, curator rejection explanations, and direct `Open Dashboard` action for approved claims.
  * Monotonic request invalidation guard (`claimsRequestId.current += 1`) in `ProfileView` triggered when the profile view is closed (`!visible`) or on auth token loss (`!authToken`), preventing in-flight claim responses from overwriting state after modal dismissal.
  * Dedicated Owner Dashboard modal (`OwnerDashboardModal`):
    * Verified owner badge (`☕ Verified Owner`).
    * Key performance indicators: LOKAL Community Rating, Total Reviews Count, and Claim Status.
    * Quick-edit form for shop Name and Address with client validation, dirty state tracking, and explicit address clearing (`null`).
    * Bounded customer reviews feed showing top 5 reviews with star ratings, author display names, and relative timestamps, omitting sensitive user UUIDs and emails.
* **Authentication & Session Lifecycle Management**:
  * User registration and login screens (`RegisterView`, `LoginView`) with input validation, password matching, inline error presentation, and loading states.
  * Hardware-backed credential persistence via `expo-secure-store` with fail-fast security preventing silent in-memory downgrades in native or production runtimes.
  * Automatic session restoration on application launch with backend profile validation against `/api/v1/auth/me`.
  * Distinct error handling for invalid sessions (automatic token purging on `401 Unauthorized`) versus transient network/server failures (credential preservation with recovery UI).
  * Dedicated restoration error recovery UI offering both **Retry** and **Sign Out** actions.
  * Fail-safe sign-out ensuring local credentials are unconditionally deleted regardless of backend network availability.
  * Monotonic operation generation guards (`operationGenerationRef`) protecting the authentication provider against asynchronous race conditions across concurrent logins, retries, and logouts.
  * Automatic Bearer token propagation across nearby coffee shop searches, review operations, AI summary requests, and favorites operations.
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
* **Advanced Nearby Coffee Shop Search & Filtering**:
  * Search coffee shops by name or street address via a debounced search input with `"Search by name or address..."` placeholder.
  * Independent dual rating filter chips for Google Places provider ratings (`Google ★ 4.0+`, etc.) and first-party LOKAL community ratings (`LOKAL ★ 4.0+`, etc.) without composite score blending.
  * Sort options supporting `'distance'` (Nearest), `'rating'` (Top Rated), and `'lokal_rating'` (Top LOKAL) with deterministic tie-breaking.
  * Distinct rating badge display on coffee shop cards: Google provider rating badge (`★ {rating}`) and first-party community badge (`☕ {rating} ★ ({count})`).
  * Explicit null semantics: shops without LOKAL reviews display no community badge; setting a minimum LOKAL rating filter strictly excludes unreviewed shops.
  * Dedicated "Clear all filters" empty state recovery action restoring default discovery parameters.
  * Pure request coordinator `NearbyShopsController` managing monotonic request sequence counters, listener subscriptions, selection synchronization, and stale-response discarding across rapid filter/sort toggling, auth session changes, and location loss.
* **Personalized Coffee Shop Recommendations ("For You" Tab)**:
  * Segmented control `[Nearby | For You]` in `NearbyShopsSheet` allowing authenticated users to toggle between location-based nearby exploration and taste-profile personalized recommendations.
  * Recommendation cards displaying match badge (`✨ Recommended For You`), coffee shop name, address, calculated distance badge (when device coordinates are available), provider rating, community rating, and synthesized explanation text.
  * Pure request coordinator `PersonalizedRecommendationsController` managing monotonic request sequence counters (`requestId`), user principal binding (`userId`), and stale-response discarding across auth transitions and coordinates updates.
  * Distinct semantic UI state handling: loading spinner with helper text, friendly guidance state for `insufficient_data` prompting users to favorite or review coffee shops to unlock personalized picks, empty state when no shops match within the radius, and localized error presentation with retry.
  * Reactive recommendation refresh triggered automatically when user favorites, unfavorites, or creates/edits/deletes reviews in `ShopDetailCard`.
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
  * `20261002000000_advanced_search_and_filters.sql`: Advanced search across shop name and street address, independent LOKAL community rating calculation (`LEFT JOIN LATERAL` on reviews), `min_lokal_rating` filtering, deterministic multi-column sorting (`distance`, `rating`, `lokal_rating`), and least-privilege security model (`SECURITY INVOKER`, execution revoked from `anon`/`PUBLIC`, granted strictly to `authenticated`).
  * `20261006000000_shop_claims.sql`: Coffee shop ownership claims table (`shop_claims`), `claim_status` enum (`PENDING`, `APPROVED`, `REJECTED`, `REVOKED`), partial unique indexes for single-approved claim per shop and single-pending claim per user/shop, atomic curation-demotion revocation trigger, approval curation check trigger, privileged `approve_shop_claim` RPC with row locking (`FOR UPDATE` on `shop_curation`), and database-computed review aggregation RPC `get_shop_review_aggregates`.
  * `20261007000000_community_feed.sql`: Chronological partial index `idx_reviews_community_feed`, `get_community_feed` stored procedure with `limit + 1` bounded pagination, approved curation enforcement, deterministic tie-breaking (`created_at DESC, id DESC`), and privacy-safe field projection.
* **Community Feed Layer & Endpoint**:
  * `GET /api/v1/community/feed`: Authenticated endpoint returning chronological first-party reviews for approved coffee shops.
  * Query parameters: `limit` (default 20, `ge=1, le=50`) and `offset` (default 0, `ge=0`).
  * `CommunityService.get_feed`: Clamps limit (`1 <= limit <= 50`), invokes `get_community_feed` RPC via scoped authenticated Supabase client carrying caller's JWT, derives authoritative `has_more = len(raw_items) > limit`, slices items to `raw_items[:limit]`, and maps sanitized database errors.
  * Pydantic schemas (`backend/app/schemas/community.py`): `CommunityFeedItem` with permitted navigation IDs (`id`, `shop_id`), shop metadata, rating, content, author display name, timestamps, and computed `is_edited` validator; `CommunityFeedResponse` with `items` and `has_more`.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Dedicated service-role database client (`backend/app/core/supabase.py`) and fail-closed FastAPI dependency `get_service_role_supabase()` (`backend/app/api/deps.py`) requiring `SUPABASE_SERVICE_ROLE_KEY` and returning `HTTP 503` if unconfigured.
* Authenticated coffee shop management via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`):
  * Public/authenticated read access for approved coffee shops.
  * Privileged shop mutations (`POST`, `PATCH`, `DELETE`) protected by `require_curator` and executed through `get_service_role_supabase()`. Direct client PostgREST mutations are denied.
* Authenticated nearby coffee shop discovery via `GET /api/v1/shops/nearby`, supporting `query` (case-insensitive name and address matching), `min_rating` (provider rating threshold), `min_lokal_rating` (first-party community rating threshold, `ge=0.0, le=5.0`), and `sort_by` (`distance`, `rating`, `lokal_rating`) with deterministic tie-breaking and response modeling via `NearbyShopResponse` (including `lokal_rating` and `lokal_reviews_count`).
* Independent business eligibility and curation layer (`APPROVED`, `EXCLUDED`, `PENDING_REVIEW`):
  * Curation inspection (`GET /api/v1/shops/{id}/curation`) and evaluation (`POST /api/v1/shops/{id}/curation/evaluate`) protected by `require_curator` and executed via `get_service_role_supabase()`.
  * Column-level grant protection ensuring direct Data API callers can only query `(shop_id, status)` for approved shops without exposing internal notes or confidence scores.
* **Favorite Coffee Shops Management & Endpoints**:
  * `GET /api/v1/favorites`: Authenticated collection endpoint returning all approved coffee shops favorited by the current user, ordered by most-recently favorited (`created_at DESC`), returning `list[FavoriteShopResponse]`. Strict user ownership isolation via RLS and caller JWT filtering; non-approved shops (`PENDING_REVIEW`, `EXCLUDED`) are excluded.
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
* **Personalized Coffee Shop Recommendation Layer & Endpoint**:
  * `GET /api/v1/shops/recommendations/personalized`: Authenticated endpoint returning personalized coffee shop recommendations tailored to caller's taste profile and geographic location.
  * Request validation (`PersonalizedRecommendationParams`): optional `latitude`, `longitude`, `radius` (default 5000m, max 50000m), and `limit` (default 5, max 5).
  * Strict interaction threshold: requires $\ge 1$ favorite or $\ge 1$ positive first-party review ($\ge 4.0$). Returns `status: "insufficient_data"` if threshold is not met.
  * Pre-limit user exclusions: retrieves user's favorited shop IDs and first-party reviewed shop IDs, filtering them out of candidate sets *before* candidate evaluation limits are applied so visited shops never starve the candidate pool.
  * Bounded candidate discovery: pages candidate shops in chunks of 30 up to `MAX_CANDIDATE_PAGES = 3` (up to 90 raw candidates), stopping immediately once 10 eligible candidates (`CANDIDATE_EVALUATION_LIMIT = 10`) are gathered. Supports both coordinate-based spatial queries and coordinate-free discovery.
  * Evaluates up to 10 candidates (`CANDIDATE_EVALUATION_LIMIT`) and returns the top 5 (`RECOMMENDATION_LIMIT = 5`).
  * 20-feature coffee ontology across 4 dimensions: Brew & Beverage Styles (`espresso`, `pour over`, `cold brew`, `filter coffee`, `matcha`, `tea`), Beans & Craft (`single origin`, `specialty coffee`, `house blend`, `light roast`, `dark roast`, `latte art`), Ambiance & Work (`quiet`, `wifi`, `cozy`, `work friendly`, `spacious`), and Bakery & Food (`pastries`, `breakfast`, `vegan options`).
  * Deterministic scoring formula:
    * User taste profile vector built from positive reviews ($\ge 4.0$) and favorites' reviews, weighted by rating ($w = 1.0 + 0.2 \times (\text{rating} - 4.0)$).
    * Candidate feature extraction from candidate first-party and external reviews.
    * $S_{\text{taste}}$ via cosine similarity. Unreviewed candidates or candidates without text reviews receive baseline $S_{\text{taste}} = 0.15$ if their provider rating is within $\pm 0.3$ (rounded to 2 decimal places) of user's favorited shops' average provider rating.
    * $S_{\text{quality}}$ from weighted composite of LOKAL community rating (70%) and provider rating (30%), falling back to provider rating.
    * $S_{\text{proximity}}$ via linear decay over search radius when coordinates are supplied.
    * Dynamic weight redistribution: $W_{\text{taste}} = 0.60, W_{\text{quality}} = 0.25, W_{\text{proximity}} = 0.15$ with coordinates; $W_{\text{taste}} = 0.70, W_{\text{quality}} = 0.30, W_{\text{proximity}} = 0.0$ without coordinates.
    * Deterministic tie-breaking: `relevance_score DESC`, then `candidate.rating DESC` (`NULLS LAST`), then `candidate.id ASC`.
  * Location-independent grounded explanation synthesis:
    * Protocol abstraction `PersonalizedExplanationSynthesizer` in `backend/app/services/personalized_explanation_synthesizer.py`.
    * `GeminiPersonalizedExplanationSynthesizer` targeting Google Gemini REST API (`gemini-2.5-flash` with `thinkingBudget: 0`).
    * Concurrent candidate explanation synthesis via `asyncio.gather` bounded by a strict batch timeout of 7.0 seconds.
    * Strictly location-independent prompt: excludes distance metrics, ensuring explanations remain valid across user coordinate updates.
    * Grounding validation: ensures synthesized explanations reference matched features and do not exceed 280 characters.
    * Deterministic fallback templates: ensures coherent, grounded explanations when Gemini is unavailable, times out, or fails validation.
  * Process-local caching with generation fencing:
    * `PersonalizedRecommendationCache` in `backend/app/services/personalized_cache.py`: caches taste profiles (1800s TTL) and explanations (3600s TTL, max 1000 items).
    * Thread-safe generation fencing (`_user_versions`) incremented via `invalidate_user()`. Cache write operations verify generation invariance, preventing in-flight stale cache writes.
    * Wired reactive cache invalidation into review endpoints (`POST`, `PATCH`, `DELETE` at `/api/v1/shops/{id}/reviews`) and favorite endpoints (`POST`, `DELETE` at `/api/v1/shops/{id}/favorite`).
* **Database Write Privilege Protection & Secure RPCs**:
  * Direct PostgREST `INSERT` and `UPDATE` on `reviews` and `favorites` revoked; writes routed through PostgreSQL `SECURITY DEFINER` RPCs (`create_user_review`, `update_user_review`, `create_user_favorite`) with `auth.uid()` derivation and revoked `PUBLIC` execution privileges.
  * Immutable author name snapshotting from user metadata with fallback to `'LOKAL User'`. Never exposes user emails or internal UUIDs in review responses.
  * Strict `source = 'lokal'` filtering across application review lookups, updates, and deletes.
* Google Places API (New) integration for transient external review retrieval with provider attribution and source links. No caching or persistence of Google review content.
* **Coffee Shop Ownership Claims & Curator Verification Gateway**:
  * `POST /api/v1/shops/{shop_id}/claim`: Validates target coffee shop exists and is `APPROVED`; enforces single pending claim per user and single approved claim per shop; creates claim in `PENDING` status.
  * `GET /api/v1/shops/{shop_id}/claim`: Retrieves caller's claim status for a shop.
  * `GET /api/v1/claims/mine`: Lists all claims submitted by the authenticated caller.
  * `GET /api/v1/claims`: Paginated claims listing with optional `status_filter` (Curator only).
  * `GET /api/v1/claims/{id}`: Detailed claim view with embedded shop details (Curator only).
  * `POST /api/v1/claims/{id}/approve`: Invokes `approve_shop_claim` RPC via `service_role`, translating database unique violation `23505` to HTTP 409 Conflict ("This coffee shop already has an approved owner"), unapproved curation `P0001` to HTTP 400 Bad Request, status change races `P0005` to HTTP 409 Conflict, and missing claim `P0002` to HTTP 404 Not Found.
  * `POST /api/v1/claims/{id}/reject`: Transitions claim to `REJECTED` with required review notes.
  * `POST /api/v1/claims/{id}/revoke`: Revokes an active approved claim (`APPROVED -> REVOKED`).
  * Least-privilege response projection (`ShopClaimResponse`): strips internal `user_id` and raw curator notes, conditionally projecting `rejection_reason` derived from `review_notes` only for `REJECTED` and `REVOKED` claims while suppressing internal notes for `PENDING` and `APPROVED` claims.
* **Coffee Shop Owner Dashboard & Shop Management Endpoints**:
  * `verify_active_owner`: Enforces active approved claim (`status = 'APPROVED'`) and validates shop curation remains `APPROVED`. Fails closed with `HTTP 403 Forbidden` if ownership is unapproved or shop curation is demoted.
  * `GET /api/v1/owner/shops/{shop_id}/dashboard`: Returns `OwnerDashboardResponse` containing full shop details, active claim info, PostgreSQL-computed `lokal_reviews_count` and `lokal_rating`, and bounded `recent_reviews` (top 5, stripping sensitive user UUIDs and emails).
  * `PATCH /api/v1/owner/shops/{shop_id}`: Allows owners to update `name` and `address` via `OwnerShopUpdate`. Strictly forbids protected/system fields (`rating`, `google_place_id`, `latitude`, `longitude`, `curation status`, etc.) using Pydantic `extra = "forbid"` (returning `HTTP 422 Unprocessable Entity`), while supporting explicit address clearing (`{"address": null}`).
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), external provider failures (`502`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **404 passing tests**, covering auth, shops, curation, nearby discovery with advanced search and filtering, external reviews, first-party user reviews, AI review summaries, AI must-try recommendations, favorite coffee shops (including the favorites list endpoint), personalized coffee shop recommendations (including taste profiling, caching, and explanation synthesis), coffee shop ownership claiming and curator verification lifecycle, owner dashboard metrics and profile editing with protected-field validation, community feed pagination and privacy filtering, curator authorization, and service-role fail-closed behavior.

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
  * `shop_claims`: Stores coffee shop ownership claims (`claimant_name`, `claimant_phone`, `claimant_role`, `business_proof`, `status`, `review_notes`, `reviewed_at`, `curator_id`, `created_at`, `updated_at`).
* **Least-Privilege Table & Column Grants**:
  * `shops`: `SELECT` granted to `anon` and `authenticated`. All direct client write grants (`INSERT`, `UPDATE`, `DELETE`) are revoked. Full `ALL` access granted strictly to `service_role`.
  * `shop_curation`: Direct table `SELECT` revoked from `anon`, `authenticated`, and `public`. Column-level `SELECT (shop_id, status)` granted to `anon` and `authenticated`. Sensitive columns (`curator_notes`, `evidence_source`, `confidence`, `curator_id`, `location_count`) are restricted from client roles. Full access granted strictly to `service_role`.
  * `menu_items`: All privileges revoked from `anon`, `authenticated`, and `public`. Granted strictly to `service_role`.
  * `shop_curation_audit`: All privileges revoked from `anon` and `public`. `SELECT` granted to `authenticated`. Full access granted strictly to `service_role`.
  * `reviews`: Direct `INSERT` and `UPDATE` revoked from client roles. `SELECT` and `DELETE` granted to `authenticated`. Full access granted to `service_role`.
  * `favorites`: Direct `INSERT` and `UPDATE` revoked from client roles. `SELECT` and `DELETE` granted to `authenticated`. Full access granted to `service_role`.
  * `shop_claims`: Direct `INSERT`, `UPDATE`, and `DELETE` revoked from `anon`, `authenticated`, and `public`. `SELECT` granted to `authenticated`. Full access granted strictly to `service_role`.
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
  * `shop_claims`:
    * Authenticated `SELECT`: Allowed for claims belonging to caller (`auth.uid() = user_id`) or where JWT `(auth.jwt() -> 'app_metadata' ->> 'role') IN ('curator', 'admin')`.
    * Mutations: Direct client mutations are blocked; mutations must proceed via FastAPI gateway using `service_role`.
* **Review Schema & Integrity**:
  * `user_id UUID REFERENCES auth.users(id) ON DELETE CASCADE`
  * `author_name TEXT NOT NULL DEFAULT 'LOKAL User'`
  * `source TEXT NOT NULL DEFAULT 'lokal'`
  * `uq_reviews_user_shop UNIQUE (user_id, shop_id)`: Enforces single review per user per coffee shop.
  * Indexes: `idx_reviews_shop_id`, `idx_reviews_user_id`, and partial chronological index `idx_reviews_community_feed ON reviews (created_at DESC, id DESC) WHERE source = 'lokal'`.
* **Favorite Schema & Integrity**:
  * `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  * `shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE`
  * `created_at TIMESTAMPTZ NOT NULL DEFAULT timezone('utc'::text, now())`
  * `uq_favorites_user_shop UNIQUE (user_id, shop_id)`: Enforces single favorite record per user per coffee shop.
  * Indexes: `idx_favorites_user_shop ON favorites (user_id, shop_id)`.
* **Shop Claims Schema & Integrity**:
  * `user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE`
  * `shop_id UUID NOT NULL REFERENCES shops(id) ON DELETE CASCADE`
  * `status claim_status NOT NULL DEFAULT 'PENDING'`
  * `idx_unique_approved_claim_per_shop UNIQUE (shop_id) WHERE status = 'APPROVED'`: Enforces exactly one approved owner per coffee shop at the database boundary.
  * `idx_unique_pending_claim_per_user_shop UNIQUE (shop_id, user_id) WHERE status = 'PENDING'`: Enforces at most one pending claim per user per coffee shop.
  * Trigger `trg_revoke_claims_on_curation_demotion` on `shop_curation`: automatically and atomically revokes active approved owner claims if a shop is demoted away from `APPROVED`.
  * Trigger `trg_check_claim_approval_curation` on `shop_claims`: verifies shop is currently `APPROVED` before allowing a claim to transition to `APPROVED`.
* **Controlled Database RPCs**:
  * `create_user_review(p_shop_id, p_rating, p_content)`: Security definer RPC validating rating (1–5), verifying shop existence and `APPROVED` curation status, enforcing uniqueness, resolving author display name snapshot from user profile metadata, and inserting review with server timestamps.
  * `update_user_review(p_shop_id, p_rating, p_content, p_update_content)`: Security definer RPC enforcing field presence, validating rating, verifying shop is `APPROVED`, enforcing caller ownership and `source = 'lokal'`, preserving server-managed fields, and updating `rating`, `content`, and `updated_at`.
  * `create_user_favorite(p_shop_id)`: Security definer RPC validating caller authentication (`auth.uid() IS NOT NULL`), verifying target shop existence and `APPROVED` curation status in `shop_curation`, inserting favorite record with server-derived `auth.uid()`, and handling duplicate conflicts idempotently.
  * `get_nearby_shops(user_lat, user_lon, radius_meters, max_results, search_query, min_rating, min_lokal_rating, sort_by, user_id)`: Security invoker spatial discovery RPC evaluating PostGIS distance against spatial index, enforcing `APPROVED` curation status, matching search query against shop name and street address via `ILIKE`, computing LOKAL community rating aggregates via `LEFT JOIN LATERAL` on `reviews (source = 'lokal')`, applying independent provider and LOKAL rating filters, and deterministically sorting candidates across `'distance'`, `'rating'`, and `'lokal_rating'`.
  * `approve_shop_claim(p_claim_id, p_curator_id, p_review_notes)`: Security definer RPC with `SET search_path = public, pg_temp`, locking `shop_curation` `FOR UPDATE` to serialize against concurrent demotions, transitioning claim to `APPROVED`, revoking execution from `PUBLIC`, `anon`, and `authenticated`, and granting strictly to `service_role`.
  * `get_shop_review_aggregates(p_shop_id)`: Security definer stable RPC with `SET search_path = public, pg_temp`, computing count and average rating across first-party reviews (`source = 'lokal'`) directly in PostgreSQL while filtering out `null` and out-of-range ratings, revoking execution from `PUBLIC` and `anon`, and granting strictly to `authenticated` and `service_role`.
  * `get_community_feed(p_limit, p_offset)`: Security definer stable RPC with `SET search_path = public, pg_temp`, inner joining `shops` and `shop_curation (status = 'APPROVED')`, ordering by `r.created_at DESC, r.id DESC`, projecting privacy-safe attributes, fetching `limit + 1` internally, returning at most `limit + 1` rows for authoritative `has_more` derivation, with execution revoked from `PUBLIC` and `anon`, and granted strictly to `authenticated` and `service_role`.
  * Stored procedure execution privileges are revoked from `PUBLIC` and `anon`, and granted strictly according to the least-privilege security model (`authenticated` for user-facing discovery, community feed, and review/favorite RPCs; `service_role` for privileged claim approval).
* **Automated Database Test Suite (`supabase/tests/`)**:
  * Executable pgTAP test suites containing **109 total assertions** across four test suites:
    * `01_rls_and_permissions.sql`: **55 assertions** verifying RLS flags, table permissions, column privileges, and allow/deny query behaviors for `anon`, ordinary `authenticated`, and curator roles.
    * `02_advanced_search_and_filters.sql`: **15 assertions** verifying `get_nearby_shops` execution permissions (denied to `anon`/`PUBLIC`, granted to `authenticated`), name/address search matching, `APPROVED`-only curation filtering, LOKAL rating aggregation, null handling for unreviewed shops, `min_lokal_rating` threshold filtering, combined filters, and deterministic sorting.
    * `03_shop_claims.sql`: **27 assertions** verifying `shop_claims` RLS policies, table permissions, partial unique indexes, curation demotion revocation, approval serialization, RPC execution permissions, and review aggregates.
    * `04_community_feed.sql`: **12 assertions** verifying `get_community_feed` execution permissions (revoked from `anon`/`PUBLIC`, granted to `authenticated` and `service_role`), deterministic ordering (`created_at DESC, id DESC`), `limit + 1` extra row pagination behavior, offset pagination, `APPROVED` curation filtering, source isolation (`source = 'lokal'`), dynamic demotion filtering, review edits/deletions, and privacy projection.

---

# Current Data / AI Architecture Direction

The project implements a hybrid review-data architecture with operational AI review summarization, grounded menu recommendations, and personalized recommendations:

```text
Google Places Reviews (external, transient)
                  +
       LOKAL User Reviews (first-party, persisted in Supabase)
                  +
           User Favorites (persisted in Supabase)
                  ↓
          FastAPI Service Layer
                  ↓
       Unified Review Domain & Taste Profiling
                  ↓
                 AI Layer
   (ReviewSummaryService, ReviewRecommendationService,
    & PersonalizedRecommendationService / Gemini)
                  ↓
             LOKAL Mobile
```

The external review layer retrieves reviews from Google Places API (New) on demand. External review content is transient and is not persisted or cached in Supabase, preserving provider attribution and policy compliance.

First-party LOKAL reviews are persisted in Supabase with author name snapshotting, rating constraints, single-review uniqueness, and RLS/RPC security.

The review domain merges first-party LOKAL reviews and external reviews into a unified provider-neutral representation (`UnifiedReview`), exposing separate external and community metrics so downstream consumers can clearly distinguish first-party feedback.

The AI layer ingests sanitized reviews from the unified review domain to generate structured review summaries (`ReviewSummaryService`), AI-grounded "Must Try" menu recommendations (`ReviewRecommendationService`), and personalized coffee shop recommendations (`PersonalizedRecommendationService`), using `GeminiReviewSummarizer`, `GeminiReviewRecommender`, and `GeminiPersonalizedExplanationSynthesizer` via HTTP requests to Google Gemini API. Summaries, must-try recommendations, taste profiles, and personalized explanations are cached in-memory with TTL and generation-guarded invalidation, without creating persistent summary or recommendation database tables.

Independent-business eligibility and curation are maintained as a separate domain concern, ensuring review, AI, and favorite operations respect public discovery eligibility rules (`APPROVED` required).

---

# Next Task

**Immediate next task: [GitHub Issue #49 — Establish Realistic MVP Validation Dataset](https://github.com/layugjohann/lokal/issues/49).**

Issue #49 is limited to preparing a repeatable, development-safe dataset and validating the existing discovery, shop-detail, review, AI-summary, Must Try, and community-feed experience against realistic data. It does not authorize UI redesigns, new features, policy changes, or production-data operations.

Agy must follow Issue #49's planning gate: inspect the repository and relevant data mechanisms, present a concrete plan, and wait for explicit Product Owner approval before creating a branch, modifying files, or writing database data.

**UI/UX work is a separate workstream.** The visual direction is approved and documented in [`docs/ui-design-spec.md`](ui-design-spec.md), but implementation has not started. Once the dataset work has proceeded through its own workflow, UI work should begin through a separate focused Issue, starting with authentication personalization. The existing map rendering and behavior remain explicitly protected.

---

# Known Blockers

**None.**

The unified review domain, AI review summarization, AI-generated "Must Try" recommendations, coffee shop favoriting, user favorites list / profile discovery, advanced search and filtering, personalized coffee shop recommendations, coffee shop owner claiming and dashboard, and community feed and social sharing are operational. External reviews remain transient and compliant with provider policies, while first-party reviews, user favorites, and shop claims are securely persisted in Supabase with RLS, triggers, and security-definer RPC protection. In-memory caching with generation versioning is active for summaries, must-try recommendations, and personalized recommendations. Mobile user authentication, review mutations, non-blocking summary cards, non-blocking recommendations cards, interactive favorite toggles, the saved coffee shops profile view, advanced search/filter chips coordinated through `NearbyShopsController`, the For You personalized recommendations tab coordinated through `PersonalizedRecommendationsController`, owner claim submissions via `ClaimShopModal` coordinated through `ShopClaimController`, the My Claims profile tab, `OwnerDashboardModal`, and the community feed coordinated through `CommunityFeedController` and `CommunityFeedView` with native social sharing are operational and verified through 404 backend tests, 209 mobile tests, 109 database pgTAP assertions, and 0 TypeScript errors.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **Limit + 1 Authoritative Pagination in Stored Procedures**: Rather than returning exact limit rows and guessing whether more data exists via `has_more = len(items) == limit` (which produces false positives when the total dataset is exactly a multiple of the limit), querying for `limit + 1` rows directly inside PostgreSQL allows the backend to authoritatively determine `has_more = len(raw_items) > limit` and slice the result to the requested limit before serialization.
* **Monotonic Request Refs for Modal Child Entity Navigation**: In modal navigation flows where selecting feed items fetches full child entities (e.g. `fetchShopById` from `CommunityFeedView`), race conditions can occur if multiple items are tapped in rapid succession or if the modal is dismissed while a fetch is in flight. Guarding async fetches with a component-level monotonic ref (`shopRequestIdRef = useRef(0)`) and incrementing it on modal dismissal guarantees older or post-dismissal responses are dropped before updating state.
* **Strict Account Isolation on Asynchronous Refresh Handlers**: In mobile controllers managing cached collections (`CommunityFeedController`), pull-to-refresh actions must evaluate whether the active principal has changed (`effectivePrincipal !== this.currentPrincipal`). If the principal has changed, items must be immediately cleared and pagination metadata reset to prevent previous-account data from remaining visible during the in-flight refresh or surviving if the refresh fails.
* **Resilient Pagination Unblocking on Refresh Errors**: When a pull-to-refresh request invalidates an active in-flight `loadMore` request and subsequently fails, the refresh error handler must ensure that `isLoadingMore` is reset to `false` alongside `isRefreshing = false`, preventing permanent pagination locks on subsequent user scrolling.
* **Active Cancellation Flag Resets**: When cancellation invalidates active in-flight operations (`cancel()`), the controller must immediately clear active loading flags (`isLoading = false`, `isLoadingMore = false`, `isRefreshing = false`) while preserving existing feed items, pagination metadata, and errors, ensuring UI loading spinners dismiss immediately upon view unmount or navigation.
* **Zero-Identifier Sanitized Native Social Sharing**: When designing social sharing integrations for mobile applications, user-facing plain-text payloads should omit sensitive database UUIDs, internal identifiers, or private user data, focusing strictly on user-readable content (shop name, address, rating, and bounded review excerpts) with graceful error handling across platform share dialog cancellations.
* **Decoupled Native Module Testing via Injected / Functional Abstractions**: In headless Node.js test runners where React Native native bridge modules (such as `Share`) cannot be imported statically without native compilation or Flow syntax errors, decoupling API calls via optional dependency injection or functional wrappers enables comprehensive headless testing against production code without adding test frameworks or mocking libraries.
* **Partial Unique Indexes for State-Filtered Multi-Entity Constraints**: Using PostgreSQL partial unique indexes (`UNIQUE (shop_id) WHERE status = 'APPROVED'`) enforces strict single-entity business invariants (e.g. exactly one approved owner per shop) directly at the storage engine level, preventing race conditions that application-level validation cannot catch, while allowing multiple historical rejected or revoked records.
* **Row-Level Locking for Cross-Entity Workflow Serialization**: When approving an ownership claim depends on shop curation status, locking the parent entity (`SELECT ... FROM shop_curation WHERE shop_id = ... FOR UPDATE`) inside the approval stored procedure serializes concurrent approval and demotion transactions, preventing approval of demoted shops or concurrent race windows.
* **Trigger-Based Atomic Lifecycle Synchronization**: When demoting a parent entity's status (e.g., transitioning shop curation from `APPROVED` to `EXCLUDED` or `PENDING_REVIEW`), using a PostgreSQL trigger (`AFTER UPDATE OF status`) to synchronously cascade status revocations to dependent entities (e.g. `shop_claims`) guarantees that both operations commit or abort together within the same database transaction.
* **Database-Side Aggregate RPCs for Scalable Metric Computation**: Instead of loading review collections into application memory or executing raw unbounded queries to compute community ratings and review counts for dashboards, defining a database-level stored procedure (`get_shop_review_aggregates`) leverages PostgreSQL relational engine performance and minimizes network I/O.
* **Request-Schema Field Forbidding (`extra = "forbid"`)**: For privileged entity updates executed via high-privilege backend database clients (`service_role`), enforcing `extra = "forbid"` at the Pydantic schema validation boundary (`OwnerShopUpdate`) explicitly rejects attempts to submit protected system fields (such as `rating`, `curation_status`, `google_place_id`, coordinates) rather than silently discarding them.
* **Least-Privilege Projection of Internal Review Notes**: When internal review notes contain sensitive curator justifications, user-facing projections (`ShopClaimResponse`) must selectively project these notes as `rejection_reason` only for negative outcome states (`REJECTED`, `REVOKED`) while omitting them for `PENDING` or `APPROVED` states to maintain least-privilege security boundaries.
* **Explicit `search_path` and RPC Execution Revocation on `SECURITY DEFINER`**: PostgreSQL `SECURITY DEFINER` functions run with the privileges of their owner. Setting an explicit `SET search_path = public, pg_temp` prevents malicious search-path hijacking, and revoking execution from `PUBLIC`, `anon`, and `authenticated` ensures privileged database procedures can only be invoked by the trusted backend `service_role`.
* **Monotonic Request Invalidation on Modal Dismissal**: Incrementing monotonic request sequence counters when dismissing views or modals (`claimsRequestId.current += 1` on `!visible`) ensures any in-flight asynchronous HTTP requests are safely discarded upon arrival and cannot resurrect or repopulate discarded component state.
* **Location-Independent Explanation Caching**: Decoupling distance from AI-synthesized explanations allows caching recommendations safely by `(user_id, shop_id)` without explanations becoming stale when the user moves coordinates between requests.
* **Pre-Limit Candidate Exclusions**: In recommendation systems filtering out shops the user has already visited or favorited, exclusions must be applied *before* candidate evaluation limits are enforced; otherwise, visited shops in the candidate window can falsely starve the eligible candidate set.
* **Candidate Paging Early Exit at Evaluation Limit**: When candidate collection requires multi-page fetching to satisfy exclusions, paging should terminate as soon as the target evaluation limit (`CANDIDATE_EVALUATION_LIMIT`) is satisfied to avoid redundant database paging and candidate review work.
* **Generation-Fenced Cache Writes**: When asynchronous operations read entity versions at request start, cache write methods must verify that the captured version still matches the current version before writing, preventing race conditions where user mutations during slow LLM calls are overwritten with stale cached data.
* **Bounded Concurrent Batch Timeouts**: When synthesizing explanations for multiple candidates concurrently via `asyncio.gather`, bounding the entire batch with a unified timeout (e.g., 7.0s) and falling back gracefully to deterministic templates guarantees strict API latency SLA compliance even during upstream provider slowdowns.
* **Rounded Float Baseline Comparisons**: When comparing candidate provider ratings to user favorite baseline averages within a floating-point tolerance (e.g. $\pm 0.3$), rounding the difference to 2 decimal places prevents floating-point precision anomalies (e.g. `0.30000000000000027 > 0.3`) from rejecting valid matches.
* **Dual Rating Independence Without Composite Blending**: Separating external provider ratings (`min_rating`) from first-party community ratings (`min_lokal_rating`) preserves data provenance and user trust, preventing arbitrary weighting schemes while allowing users to filter along either or both axes independently.
* **`LEFT JOIN LATERAL` for Candidate Aggregation in Geospatial RPCs**: Aggregating relational review metrics (average rating, review count) for spatially-filtered candidates using `LEFT JOIN LATERAL` computes aggregates only for shops within the candidate bounding set, avoiding full-table scans.
* **Explicit Null Semantics in Optional Rating Dimensions**: In community review systems where unreviewed shops have no ratings, returning `null` for `lokal_rating` rather than defaulting to `0` clearly differentiates unrated shops from poorly rated shops. Active minimum rating filters must strictly exclude `null` ratings.
* **Pure Controller Extraction for Headless Lifecycle Verification**: When UI frameworks or Node test runners lack headless React hook renderers, extracting pure controller classes (`NearbyShopsController`) that encapsulate monotonic request sequencing, listener dispatch, and stale-response discarding allows direct, dependency-free testing of asynchronous race conditions against actual production code.
* **Least-Privilege RPC Access Model**: Unless an RPC is intentionally exposed to unauthenticated public callers, stored procedures should have permissions revoked from `anon` and `PUBLIC` and granted strictly to `authenticated`, aligning database execution privileges with API gateway authentication requirements.
* **Principal-Bound Instance Keys for Identity Boundaries**: Component keys in authentication-sensitive flows should be bound to the authenticated principal (`user.id`) rather than raw credential tokens (`authToken`). This ensures switching accounts forces a clean remount and state reset, while credential refreshes for the same user do not cause unnecessary unmounting or UI state churn.
* **Dual Defense for Session State Isolation**: Combining component key-based remounting at the view layer with principal-aware request sequencing at the controller layer guarantees that even if a replacement session's network request fails, previous-account state can never survive or be exposed.
* **Monotonic Mutation Ownership Guards**: Asynchronous mutation success callbacks (`onFavoriteChange`) must verify that the active mutation ID still matches the current sequence counter before updating parent state, preventing out-of-order mutations from corrupting parent collections.
* **Authoritative Reconciliation on Dual-State Mutations**: Optimistic UI removal provides instant feedback for destructive actions (unfavoriting), but re-favoriting should trigger authoritative collection refetches rather than synthesizing partial objects from local state.
* **Safe Distance Badge Omission with `Number.NaN`**: When distance calculation inputs (device location) are unavailable, defaulting to `Number.NaN` allows downstream formatting functions (`formatDistance`) to cleanly omit distance badges rather than displaying misleading `"0 m"` values.
* **Pure Logic Extraction for Headless Testability**: In environments lacking full component or hook renderers (such as Node.js test runners), extracting state sequencing into pure controller classes (`FavoritesController`) allows testing complex async races, session switches, and error paths against real production code without extra testing dependencies.
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

**Last Updated:** Phase 3 — MVP Polish & Validation (Issue #49 open; approved UI direction documented; UI personalization not yet implemented)
