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

## GitHub Issue #13 — Coffee Shop CRUD API

**Status:** ✅ Completed

### Completed Work

* Defined Pydantic models in `backend/app/schemas/shop.py` (`ShopBase`, `ShopCreate`, `ShopUpdate`, `ShopResponse`) enforcing validation constraints on coffee shop names, coordinate boundaries (`-90.0 <= latitude <= 90.0`, `-180.0 <= longitude <= 180.0`), rating boundaries (`0.0 <= rating <= 5.0`), and optional Google Places identifiers.
* Implemented five authenticated REST endpoints in `backend/app/api/v1/endpoints/shops.py`:
  * `POST /api/v1/shops` (`201 Created`): Creates a coffee shop record in Supabase PostgreSQL; maps duplicate `google_place_id` conflicts to `409 Conflict`.
  * `GET /api/v1/shops` (`200 OK`): Lists coffee shops ordered by name with query pagination support (`limit` default 50, `offset` default 0).
  * `GET /api/v1/shops/{shop_id}` (`200 OK`): Retrieves a single coffee shop by UUID with `404 Not Found` handling for nonexistent records and `422` for malformed UUIDs.
  * `PATCH /api/v1/shops/{shop_id}` (`200 OK`): Sole update endpoint performing partial updates; rejects empty payloads with `400 Bad Request`, rejects explicit `null` on required fields with `422 Unprocessable Entity`, and maps duplicate place IDs to `409 Conflict`.
  * `DELETE /api/v1/shops/{shop_id}` (`200 OK`): Deletes a coffee shop record by UUID and returns a standard confirmation message (`MessageResponse`).
* Created request-scoped Supabase client `get_authenticated_supabase` in `backend/app/api/deps.py` backed by `create_scoped_supabase_client(token)` in `backend/app/core/supabase.py`. PostgREST queries carry the caller's verified Bearer JWT while preserving the global shared client instance without session mutation.
* Sanitized backend error handling across all shop endpoints, logging full exception traces server-side while returning generic error messages to clients to prevent internal implementation disclosure.
* Added comprehensive automated test suite in `backend/tests/test_shops.py` (36 tests) covering authentication enforcement, field boundaries, error mapping, CRUD workflows, and request-scoped client isolation.
* Verified zero regressions across the entire backend suite (62 passing tests).

---

# Project Progress

| Feature                                    | Status      |
| ------------------------------------------ | ----------- |
| Engineering Foundation                     | ✅ Complete |
| Issue #1 — Initialize Mobile Application   | ✅ Complete |
| Issue #3 — Initialize FastAPI Backend      | ✅ Complete |
| Issue #5 — Initialize Supabase Integration | ✅ Complete |
| Issue #7 — Database Schema                 | ✅ Complete |
| Issue #9 — User Authentication             | ✅ Complete |
| Issue #11 — Maps & Location Integration    | ✅ Complete |
| Issue #13 — Coffee Shop CRUD API           | ✅ Complete |
| Coffee Shop Discovery / Search             | ⏳ Planned  |
| AI Review Summaries                        | ⏳ Planned  |

---

# Current Mobile Capabilities

The React Native (Expo) mobile application currently provides:

* Interactive map visualization via `react-native-maps`.
* Device foreground location permission requests via `expo-location`.
* Automatic user coordinate acquisition and animated map re-centering.
* Current user location representation via map marker and native user location indicators.
* Sensible fallback region (Metro Manila) when location access is pending or unavailable.
* Graceful, non-crashing permission denial handling with informative status banners.
* Differentiated terminal denial handling (`canAskAgain: false`) providing direct system settings navigation via `Linking.openSettings()`.
* Dedicated handling for undetermined permission states.
* Zero external UI dependencies, adhering to scope discipline and clean architecture.

Coffee shop search, markers, AI review summaries, and background location tracking remain outside the scope of Issue #11.

---

# Current Backend Capabilities

The FastAPI backend currently provides:

* Application configuration through environment variables.
* Basic health-check endpoints (`/health` and `/api/v1/health`).
* Supabase client initialization through `backend/app/core/supabase.py` with lazy loading, HTTPS enforcement, and isolated request-scoped authenticated client instantiation (`create_scoped_supabase_client`).
* Initial database schema migration DDL located at `supabase/migrations/20260811000000_initial_schema.sql`.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Authenticated coffee shop management via REST API (`POST`, `GET`, `PATCH`, `DELETE` at `/api/v1/shops`).
* Request-scoped caller JWT propagation (`get_authenticated_supabase`) for secure PostgREST database queries.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated testing suite executed via Python's standard library `unittest` runner (62 passing tests).

---

# Next Task

The next feature should be defined through the next GitHub Issue (such as mobile coffee shop integration or nearby shop discovery) and approved implementation plan before development begins.

---

# Known Blockers

**None.**

---

# Session Learnings

The Issue #13 development cycle established key backend engineering practices:

* **Request-Scoped Supabase Client**: PostgREST queries should carry the caller's JWT rather than the anonymous client key so that future Row Level Security (RLS) policies can identify `auth.uid()`. Constructing a fresh client instance with the caller's Authorization header ensures query isolation without mutating global singleton clients.
* **REST Semantic Discipline**: Distinguishing between client-caused validation errors (`422`), empty update requests (`400`), nonexistent resource requests (`404`), unique constraint violations (`409`), and unexpected server-side errors (`500`) yields predictable, standard API behavior.
* **Information Disclosure Prevention**: Catching internal server errors, logging full exception details internally, and returning generic error details to API clients prevents leaking database structure or environment details.
* **Pydantic Pre-Validation (`mode='before'`)**: Using `mode='before'` validators allows distinguishing between omitted optional fields in partial update payloads (`PATCH`) and explicit `null` values that violate non-null database constraints.

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

**Last Updated:** Phase 1 — Project Bootstrapping (after completion of GitHub Issue #13)


