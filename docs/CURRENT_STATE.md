# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, and external review data layer are established.

The project is now building application-level features that provide the foundation for LOKAL's future AI capabilities, including independent/local business eligibility and curation.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed feature, **Independent Business Eligibility & Shop Curation (GitHub Issue #22)**, establishes a provider-neutral curation layer that determines whether discovered coffee shops are eligible for public LOKAL discovery.

The backend now evaluates business eligibility using observable location-count evidence, persists curation state and audit history, supports curator-only manual overrides, and exposes only approved shops through nearby discovery. External review retrieval remains available through the separate provider-neutral review layer, with external review content kept transient rather than persisted in Supabase.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #22 — Independent Business Eligibility & Shop Curation

**Status:** ✅ Completed

### Completed Work

* Added provider-neutral business curation states: `APPROVED`, `EXCLUDED`, and `PENDING_REVIEW`.
* Implemented fail-closed eligibility classification: businesses with six or more locations are excluded, businesses proven to have five or fewer locations are approved, and insufficient or ambiguous evidence remains pending review.
* Added Google Places API (New) provider integration for business-location evidence using a minimal explicit field mask.
* Added deduplication using provider `places.id` and normalized physical addresses so multiple provider results do not inflate location counts.
* Added curation persistence and audit history with protected access controls.
* Added authenticated shop evaluation and curator-only manual override flows with audit logging.
* Initialized newly created shops as `PENDING_REVIEW` without performing a synchronous provider call.
* Updated nearby discovery to expose only `APPROVED` shops and avoid runtime provider calls during public discovery.
* Added concurrency protection so stale evaluations cannot overwrite newer curation decisions.
* Added robust handling for malformed provider pagination data and test isolation when provider credentials are unavailable.
* Kept business eligibility and curation separate from the provider-neutral external review architecture.
* Completed verification with **22 backend curation tests**, **2 nearby-discovery tests**, **125 backend regression tests passing**, **15 mobile tests passing**, and **TypeScript type checking passing with zero errors**.
* CodeRabbit findings were evaluated and the actionable findings were resolved before the Pull Request was merged.
* Pull Request #23 was successfully merged into `main`, closed, and its feature branch was deleted.

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
| AI-Assisted Engineering Workflow                 | ✅ Complete |
| LOKAL User Reviews                               | ⏳ Planned  |
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
* External review display within the coffee shop detail experience.
* Provider attribution and source/report links for externally sourced reviews.
* Protection against stale asynchronous review responses.
* Non-blocking review loading and retry behavior.
* Zero external UI dependencies, maintaining scope discipline and clean architecture.

AI review summaries, Must-Try recommendations, LOKAL user reviews, and background location tracking remain outside the current implementation scope.

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
* Provider-neutral review schemas and service abstractions for external and future first-party reviews.
* Google Places API (New) integration for transient external review retrieval.
* Authenticated `GET /api/v1/shops/{shop_id}/reviews` review endpoint.
* Provider attribution and provenance metadata in review responses.
* Sanitized external-provider error handling with `502 Bad Gateway` semantics.
* No persistence or caching of Google review content or author information.
* Robust error handling distinguishing client input errors (`400`/`422`), missing records (`404`), unique constraint conflicts (`409`), external provider failures (`502`), service unavailability (`503`), and sanitized generic server failures (`500`).
* Automated backend regression testing with **125 passing tests**, including dedicated curation and nearby-discovery coverage.

---

# Current Data / AI Architecture Direction

The project now implements the first stage of the intended hybrid review-data architecture:

```text
Google Places Reviews (external, transient)
                  +
       LOKAL User Reviews (future)
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

The external review layer currently uses Google Places API (New) through the FastAPI backend. External review content and author information are not persisted in Supabase, and no caching layer has been introduced because the applicable provider policy did not provide sufficient confidence for those behaviors.

The review domain is provider-neutral so that future LOKAL-owned reviews can coexist with externally sourced reviews without requiring separate downstream review-processing pipelines.

The AI layer remains a future consumer of the unified review domain. AI implementation is intentionally deferred until the applicable external-data and AI-processing requirements are established.

Independent-business eligibility and curation are implemented as a separate application concern. The curation layer determines public discovery eligibility without coupling business classification to the review provider.

---

# Next Task

The next feature should be defined through the next GitHub Issue after reviewing the current application state and the completed curation architecture.

The next capability should build on the now-established distinction between **business eligibility**, **external review data**, and **future AI processing**.

Before implementation:

1. Review the current database schema, coffee shop model, curation layer, review layer, and existing APIs.
2. Define the next product requirement and observable acceptance criteria.
3. Review implications for nearby discovery, search/filtering, and future AI capabilities.
4. Create and approve the next GitHub Issue.
5. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

Google Places integrations are currently implemented through separate business-curation and external-review provider layers. AI processing of external review content remains a future architectural/policy consideration, not a current blocker.

---

# Session Learnings

The recent development cycles established the following engineering practices:

* **Request-Scoped Supabase Client**: PostgREST queries should carry the caller's JWT rather than relying on a shared anonymous session so that future Row Level Security (RLS) policies can identify `auth.uid()`.
* **REST Semantic Discipline**: Distinguishing between client-caused validation errors (`400`/`422`), nonexistent resources (`404`), unique constraint violations (`409`), external provider failures (`502`), service unavailability (`503`), and unexpected server-side errors (`500`) yields predictable API behavior.
* **Information Disclosure Prevention**: Internal server errors should be logged server-side while clients receive sanitized error messages.
* **Pydantic Pre-Validation**: `mode='before'` validators can distinguish omitted fields in partial update payloads from explicit `null` values that violate required database constraints.
* **Deterministic Geospatial Pagination**: Nearby search pagination requires a stable secondary ordering key (`id`) in addition to distance.
* **Async Race Protection**: Location-driven discovery and external review requests should prevent stale responses from overwriting newer state.
* **Provider-Neutral Domain Modeling**: External providers should be isolated behind provider abstractions so downstream application and AI layers are not coupled to a specific provider.
* **External Data Policy Discipline**: External review content should not be persisted or cached unless the provider's current policies clearly permit those behaviors.
* **Fractional Rating Support**: External review ratings should preserve the provider's numeric precision rather than assuming integer-only ratings.
* **Review-Driven Iteration**: CodeRabbit findings must be evaluated critically, classified, fixed when actionable, and re-verified until no actionable findings remain.
* **Fail-Closed Eligibility**: Business eligibility should default to hidden/pending when evidence is insufficient rather than risk exposing unsupported businesses.
* **Curation State Separation**: Business eligibility is an independent domain concern and should not be inferred from review-provider availability.
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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #22 and merge of PR #23)
