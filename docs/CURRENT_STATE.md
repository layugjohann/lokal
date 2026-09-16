# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, and nearby coffee shop discovery are established.

The project is now moving from infrastructure and foundation work into application-level features, with the review data layer identified as the next major capability needed to support LOKAL's AI features.

---

# Current Status

🟢 **On Track**

The core application stack is operational and the latest completed feature, Coffee Shop Discovery & Nearby Search, is implemented and verified across the backend and mobile application.

The mobile app currently supports authenticated location-aware coffee shop discovery through an interactive map and nearby shop list. The backend provides authenticated coffee shop management and nearby search using geospatial filtering and deterministic distance ordering.

The engineering workflow has also been formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #15 — Coffee Shop Discovery & Nearby Search

**Status:** ✅ Completed

### Completed Work

* Added authenticated `GET /api/v1/shops/nearby` endpoint for discovering coffee shops near a supplied latitude and longitude.
* Added configurable search radius with a default of 5,000 meters and a maximum of 50,000 meters.
* Added latitude/longitude validation and pagination through `limit` and `offset`.
* Implemented Supabase SQL RPC geospatial search using bounding-box filtering followed by Haversine distance calculation.
* Added handling for antimeridian longitude boundaries and polar edge cases.
* Used an Earth radius of 6,371,000 meters for distance calculations.
* Added deterministic ordering using `distance_meters ASC, id ASC` so pagination remains stable when shops have equal distances.
* Added mobile map markers for nearby coffee shops.
* Added nearby coffee shop list/bottom-sheet presentation and shop detail selection.
* Added loading, empty-state, location-error, API-error, and stale-selection handling.
* Propagated the authenticated user's access token from the application layer to the discovery request and removed the public-token fallback.
* Added monotonic request tracking to prevent stale asynchronous responses from overwriting newer discovery results.
* Added automated tests covering the discovery functionality and regression behavior.
* Final verification completed with **83 backend tests passing**, **10 mobile tests passing**, and **TypeScript type checking passing with zero errors**.
* CodeRabbit review findings were evaluated and resolved; the final re-review reported no remaining actionable findings.

---

# Project Progress

| Feature / Milestone                         | Status      |
| ------------------------------------------- | ----------- |
| Engineering Foundation                      | ✅ Complete |
| Issue #1 — Initialize Mobile Application    | ✅ Complete |
| Issue #3 — Initialize FastAPI Backend       | ✅ Complete |
| Issue #5 — Initialize Supabase Integration  | ✅ Complete |
| Issue #7 — Database Schema                  | ✅ Complete |
| Issue #9 — User Authentication              | ✅ Complete |
| Issue #11 — Maps & Location Integration     | ✅ Complete |
| Issue #13 — Coffee Shop CRUD API            | ✅ Complete |
| Issue #15 — Coffee Shop Discovery & Search  | ✅ Complete |
| AI-Assisted Engineering Workflow             | ✅ Complete |
| External Review Data Layer                  | ⏳ Next     |
| LOKAL User Reviews                          | ⏳ Planned  |
| AI Review Summaries                         | ⏳ Planned  |
| AI Must-Try Recommendations                 | ⏳ Planned  |

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
* Zero external UI dependencies, maintaining scope discipline and clean architecture.

AI review summaries, Must-Try recommendations, user reviews, and background location tracking remain outside the current implementation scope.

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
* Authenticated nearby coffee shop discovery via `GET /api/v1/shops/nearby`.
* Supabase SQL RPC-based geospatial search with radius filtering, Haversine distance calculation, pagination, antimeridian handling, and deterministic distance ordering.
* Request-scoped caller JWT propagation (`get_authenticated_supabase`) for secure PostgREST database queries.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **83 passing tests**.

---

# Current Data / AI Architecture Direction

The project is intentionally moving toward a hybrid review-data architecture:

```text
External Reviews (initial data source)
              +
      LOKAL User Reviews (future)
              ↓
       FastAPI Review Layer
              ↓
      Unified Review Dataset
              ↓
            AI Layer
     summarization / recommendations
              ↓
         LOKAL Mobile
```

The immediate priority is to investigate and design the external review data layer before implementation. The project should not assume that a particular review provider can be scraped, stored, or redistributed without verifying its current API capabilities and usage restrictions.

The eventual architecture should allow externally sourced reviews and first-party LOKAL reviews to coexist as distinct sources within a unified review domain so that downstream AI functionality does not need separate review-processing pipelines.

---

# Next Task

The next feature should be defined through the next GitHub Issue after the external review-data architecture and provider constraints have been investigated.

The next planned capability is the **External Review Data Layer**, which should establish how LOKAL initially obtains review data that can later feed the unified review dataset and AI layer.

Before implementation:

1. Review the current database schema, coffee shop model, and existing APIs.
2. Investigate viable external review providers and their current API/data-use constraints.
3. Define the review fields and provenance metadata required by LOKAL.
4. Decide which external review data should be persisted versus fetched dynamically.
5. Design the unified review model so external and future LOKAL reviews can coexist.
6. Define the API boundary between the review layer and the AI layer.
7. Create and approve the next GitHub Issue.
8. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

Provider/API constraints for external review data are an **investigation requirement**, not currently a project blocker.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **Request-Scoped Supabase Client**: PostgREST queries should carry the caller's JWT rather than relying on a shared anonymous session so that future Row Level Security (RLS) policies can identify `auth.uid()`.
* **REST Semantic Discipline**: Distinguishing between client-caused validation errors (`400`/`422`), nonexistent resources (`404`), unique constraint violations (`409`), and unexpected server-side errors (`500`) yields predictable API behavior.
* **Information Disclosure Prevention**: Internal server errors should be logged server-side while clients receive sanitized error messages.
* **Pydantic Pre-Validation**: `mode='before'` validators can distinguish omitted fields in partial update payloads from explicit `null` values that violate required database constraints.
* **Deterministic Geospatial Pagination**: Nearby search pagination requires a stable secondary ordering key (`id`) in addition to distance.
* **Async Race Protection**: Location-driven discovery requests should prevent stale responses from overwriting newer state.
* **Review-Driven Iteration**: CodeRabbit findings must be evaluated critically, classified, fixed when actionable, and re-verified until no actionable findings remain.
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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #15 and merge of PR #17)
