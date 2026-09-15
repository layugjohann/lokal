# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 1 — Project Bootstrapping**

The engineering foundation, mobile application foundation, backend foundation, initial Supabase integration, database schema, user authentication foundation, and mobile maps/location foundation have been established. The project is now ready for application feature development (such as coffee shop CRUD APIs, discovery search, and favorites).

---

# Current Status

🟢 **On Track**

The development environment, engineering workflow, mobile application foundation, FastAPI backend, Supabase database schema, authentication system, and interactive maps/location integration are fully established and verified.

The mobile app provides location permission management, user coordinate acquisition, interactive map browsing, terminal permission denial handling with system settings navigation, and smooth user location rendering.

The backend provides user registration, login, logout, and token-based authentication verification associating authenticated requests directly with Supabase `auth.users.id`.

The repository is ready for the next feature-development cycle.

---

# Latest Completed Feature

## GitHub Issue #15 — Coffee Shop Discovery & Nearby Search

**Status:** ✅ Completed

### Completed Work

* **Database Migration & SQL RPC**:
  * Implemented `get_nearby_shops(...)` stored procedure in `supabase/migrations/20260916000000_nearby_shops_rpc.sql`.
  * Utilizes a planar bounding-box prefilter (`lat_min` to `lat_max`, `lng_min` to `lng_max`) to query the existing `idx_shops_lat_lng` index on `shops (latitude, longitude)`.
  * Calculates exact great-circle distance using the spherical Haversine formula with Earth radius `6,371,000.0` meters, returning `distance_meters`.
  * Enforces deterministic offset pagination using a primary-key tie-breaker (`ORDER BY calc.distance_meters ASC, calc.id ASC`).
  * Explicitly handles $\pm 180^\circ$ antimeridian crossing using split longitude interval logic and handles polar bounds ($|\text{latitude}| \ge 89.9^\circ$) with full longitude coverage (`spans_all_lng`).
  * Declared with `SECURITY INVOKER` and `STABLE` to respect caller privileges and future Row Level Security policies.
* **FastAPI Backend**:
  * Defined `NearbyShopResponse` in `backend/app/schemas/shop.py` (and re-exported via `backend/app/schemas/__init__.py`), extending `ShopResponse` with `distance_meters: float`.
  * Implemented `GET /api/v1/shops/nearby` in `backend/app/api/v1/endpoints/shops.py`, positioned before `/{shop_id}` to ensure unambiguous route resolution.
  * Validates query parameters:
    * `latitude`: `float` between `-90.0` and `90.0`
    * `longitude`: `float` between `-180.0` and `180.0`
    * `radius`: `float` between `0.0` and `50,000.0` meters (default `5,000.0`m)
    * `limit`: `int` between `1` and `100` (default `50`)
    * `offset`: `int` $\ge 0$ (default `0`)
  * Enforces Bearer JWT authentication via `get_current_user` and request-scoped caller client `get_authenticated_supabase`.
  * Sanitizes internal exceptions into generic client error responses while recording full diagnostic details in server logs.
* **Mobile Client (React Native & Expo)**:
  * Defined shared models in `mobile/src/types/shop.ts` (`Shop`, `NearbySearchParams`).
  * Created `mobile/src/services/shopService.ts` providing backend communication (`fetchNearbyShops`) and formatting helpers (`formatDistance`, `formatRating`). Client routes all traffic through the FastAPI backend with zero direct Supabase access.
  * Created custom hook `mobile/src/hooks/useNearbyShops.ts` managing nearby shop retrieval, loading indicators, API error states, and selection tracking.
  * Mitigated asynchronous race conditions using a monotonic request identifier (`requestIdRef`) to ensure older inflight responses never overwrite newer coordinates.
  * Built `mobile/src/components/NearbyShopsSheet.tsx` providing a bottom panel with shop count, loading spinners, error retry actions, empty result handling, and horizontal swipeable shop cards.
  * Built `mobile/src/components/ShopDetailCard.tsx` presenting name, rating, distance, address, and dismiss interaction for the selected shop.
  * Integrated coffee shop map markers into `mobile/src/components/LokalMapView.tsx` with coffee-brown pin styling and selected highlight state, while preserving device location acquisition, fallback regions, and permission denial banners.
* **Automated Testing & Verification**:
  * Added 21 backend tests in `backend/tests/test_nearby_shops.py` covering success states, custom parameters, distance ordering, empty results, boundary validations, authentication enforcement, database exception sanitization, route precedence, and geodesic math benchmarks.
  * Added 10 mobile unit tests in `mobile/tests/` covering distance formatting, rating formatting, base URL resolution, request construction, unauthenticated headers, selection synchronization, and race condition handling.
  * Verified 83 passing backend tests (zero regressions from 62 previous tests), 10 passing mobile tests, and clean TypeScript typecheck (`0` errors).

---

# Project Progress

| Feature                                           | Status      |
| ------------------------------------------------- | ----------- |
| Engineering Foundation                            | ✅ Complete |
| Issue #1 — Initialize Mobile Application          | ✅ Complete |
| Issue #3 — Initialize FastAPI Backend             | ✅ Complete |
| Issue #5 — Initialize Supabase Integration        | ✅ Complete |
| Issue #7 — Database Schema                        | ✅ Complete |
| Issue #9 — User Authentication                    | ✅ Complete |
| Issue #11 — Maps & Location Integration           | ✅ Complete |
| Issue #13 — Coffee Shop CRUD API                  | ✅ Complete |
| Issue #15 — Coffee Shop Discovery & Nearby Search | ✅ Complete |
| AI Review Summaries                               | ⏳ Planned  |

---

# Current Mobile Capabilities

The React Native (Expo) mobile application currently provides:

* Interactive map visualization via `react-native-maps`.
* Foreground device location permission management via `expo-location`.
* Automatic user coordinate acquisition and animated map re-centering.
* Current user location representation via native marker and map indicators.
* Sensible fallback region (Metro Manila) when location access is pending or unavailable.
* Graceful, non-crashing permission denial handling with informative status banners.
* Differentiated terminal denial handling (`canAskAgain: false`) providing direct system settings navigation via `Linking.openSettings()`.
* Nearby independent coffee shop discovery requested exclusively through the FastAPI backend (`GET /api/v1/shops/nearby`).
* Distinct coffee-themed map markers for nearby shops with active selection highlighting.
* Bottom sheet results panel (`NearbyShopsSheet`) with shop count, horizontal swipeable cards, loading indicators, empty result notices, and API error/retry actions.
* Shop detail card view (`ShopDetailCard`) with formatted distance, rating, physical address, and dismiss interaction.
* Asynchronous request sequence protection discarding stale out-of-order responses.
* Zero external UI dependencies, adhering to scope discipline and clean architecture.

---

# Current Backend Capabilities

The FastAPI backend currently provides:

* Application configuration through environment variables.
* Basic health-check endpoints (`/health` and `/api/v1/health`).
* Supabase client initialization through `backend/app/core/supabase.py` with lazy loading, HTTPS enforcement, and isolated request-scoped authenticated client instantiation (`create_scoped_supabase_client`).
* Database schema migrations including initial tables and nearby search RPC:
  * `supabase/migrations/20260811000000_initial_schema.sql`
  * `supabase/migrations/20260916000000_nearby_shops_rpc.sql`
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Authenticated coffee shop CRUD operations via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`).
* Authenticated nearby coffee shop discovery (`GET /api/v1/shops/nearby`) supporting coordinate bounding-box prefiltering, spherical Haversine distance, antimeridian handling, polar edge case handling, and deterministic offset pagination (`distance_meters ASC, id ASC`).
* Request-scoped caller JWT propagation (`get_authenticated_supabase`) for secure PostgREST database queries.
* Robust error handling distinguishing client validation errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Comprehensive automated testing suite executed via Python's standard library `unittest` runner (83 passing tests).

---

# Next Task

The next feature should be defined through the next GitHub Issue (such as AI-generated review summaries, favorites, or mobile authentication state management) and approved implementation plan before development begins.

---

# Known Blockers

**None.**

---

# Session Learnings

The Issue #15 development cycle established key full-stack engineering practices:

* **Bounding-Box Prefiltering with Spatial B-Tree Indexes**: Combining planar bounding-box prefiltering with Haversine distance enables efficient indexed spatial queries on standard B-Tree `(latitude, longitude)` indexes without requiring heavy spatial extensions like PostGIS.
* **Deterministic Pagination in Geodesic Queries**: When sorting results by computed floating-point distances, tie-breaking on the primary key (`ORDER BY distance_meters ASC, id ASC`) prevents duplication or omission across paginated queries.
* **Asynchronous Monotonic Request Tracking**: In mobile map applications where location updates can trigger overlapping fetch requests, tracking a monotonic request ID ref discards out-of-order responses and prevents stale coordinate results from overwriting newer user state.
* **Decoupled Client Authentication Injection**: Components communicating with authenticated backend endpoints should accept explicit session tokens through props/hooks rather than relying on global public environment variables, ensuring clean architectural boundaries.
* **Route Precedence in FastAPI**: Static or specialized sub-paths (`/nearby`) must be declared prior to dynamic parameterized sub-paths (`/{shop_id}`) to eliminate routing ambiguity and prevent valid string paths from triggering UUID path validation errors.

---

# Development Session Reminder

Every new feature should begin by following the workflow defined in:

* `docs/workflow.md`
* `AGENTS.md`

Before implementation:

1. Synchronize with `main`.
2. Verify a clean working tree.
3. Review this document.
4. Create the GitHub Issue.
5. Create the feature branch.
6. Review the implementation plan.
7. Obtain Product Owner approval.
8. Begin implementation.

After implementation:

1. Run the required verification steps.
2. Review CodeRabbit feedback.
3. Resolve accepted findings.
4. Merge the feature into `main`.
5. Synchronize the local `main` branch.
6. Update this document to reflect the new state.
7. Commit and push the updated `CURRENT_STATE.md`.

---

**Last Updated:** Phase 1 — Coffee Shop Discovery & Nearby Search (after implementation of GitHub Issue #15)



