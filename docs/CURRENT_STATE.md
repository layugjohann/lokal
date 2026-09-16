# CURRENT_STATE

This document provides a snapshot of the **current state of the `main` branch** of the LOKAL project. It should be updated **only after a feature or documentation change has been successfully merged into `main`** and should reflect the project's present state—not its history.

---

# Current Phase

**Phase 2 — Core Application Features**

The project bootstrapping phase is complete. The mobile application foundation, FastAPI backend, Supabase integration, database schema, user authentication, maps/location integration, coffee shop CRUD API, nearby coffee shop discovery, and external review data layer are established.

The project is now building application-level features that provide the foundation for LOKAL's future AI capabilities.

---

# Current Status

🟢 **On Track**

The core application stack is operational. The latest completed feature, **External Review Data Layer & Unified Review Architecture (GitHub Issue #19)**, establishes a provider-neutral review layer spanning the mobile application, FastAPI backend, and Google Places API (New).

The mobile app can now request and display externally sourced reviews for supported coffee shops, including provider attribution and source/report links. The backend normalizes external review data into a unified provider-neutral model while keeping external review content transient rather than persisting it in Supabase.

The engineering workflow is formalized as the **AI-Assisted Engineering Workflow**, including implementation planning, Product Owner approval, dedicated feature branches, automated verification, CodeRabbit review, iterative review resolution, and human-controlled merging.

The next feature cycle should begin only after the current state is synchronized and the next GitHub Issue and implementation plan have been approved.

---

# Latest Completed Feature

## GitHub Issue #19 — External Review Data Layer & Unified Review Architecture

**Status:** ✅ Completed

### Completed Work

* Added a provider-neutral `UnifiedReview` domain model with review source, rating, text, original text, language, author attribution, publication time, relative time, and report URL fields.
* Added provider-neutral attribution metadata through `ProviderAttribution` and `ShopReviewsResponse`.
* Added a Google Places API (New) review provider using Place Details and an explicit field mask for review and attribution fields.
* Added authenticated `GET /api/v1/shops/{shop_id}/reviews` endpoint for retrieving external reviews through the FastAPI review layer.
* Kept the Google Places API key exclusively on the backend; the mobile application does not call Google Places directly.
* Used each shop's existing `google_place_id` as the external provider identifier.
* Added graceful handling for shops without a `google_place_id`, returning an empty successful response rather than treating the absence as a provider failure.
* Added sanitized provider failure handling with `502 Bad Gateway` semantics for external API failures.
* Added malformed/invalid provider-response handling so unexpected JSON or normalization failures are converted into sanitized provider errors rather than leaking as generic server errors.
* Preserved fractional review ratings such as `4.5` through the unified schema and added regression coverage.
* Added mobile review retrieval and display in the coffee shop detail experience.
* Added provider attribution notices and source/report navigation for externally sourced reviews.
* Added conditional non-interactive provider attribution when a source URL is unavailable.
* Added request sequencing to prevent stale review responses from overwriting the currently selected coffee shop's review state.
* Required authenticated access tokens for review requests and propagated authentication through the mobile review service.
* Intentionally did **not** persist Google review content or author information in Supabase.
* Intentionally did **not** add caching because the applicable external-data policy was not sufficiently clear to justify persistence or caching.
* Kept AI summarization and Must-Try recommendation generation outside the implementation scope; the review layer now provides the architectural boundary for those future capabilities.
* Kept independent-business eligibility, chain detection, and shop curation outside the review layer and reserved them for a separate future feature.
* Completed verification with **101 backend tests passing**, **15 mobile tests passing**, and **TypeScript type checking passing with zero errors**.
* CodeRabbit findings were evaluated and the actionable findings were resolved before the Pull Request was merged.
* Pull Request #20 was successfully merged into `main`, closed, and its feature branch was deleted.

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
| AI-Assisted Engineering Workflow                 | ✅ Complete |
| Independent Business Eligibility & Shop Curation | ⏳ Planned  |
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

AI review summaries, Must-Try recommendations, LOKAL user reviews, independent-business curation, and background location tracking remain outside the current implementation scope.

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
* Automated backend regression testing with **101 passing tests**.

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

Independent-business eligibility and chain detection are intentionally separate from the review provider architecture. The review layer should not determine whether a coffee shop is considered independent or local.

---

# Next Task

The next feature should be defined through the next GitHub Issue after reviewing the current application state and the requirements for independent/local business discovery.

The next planned capability is **Independent Business Eligibility & Shop Curation**, which should establish how LOKAL distinguishes supported independent/local coffee businesses from larger chains and how inclusion/exclusion decisions are represented without coupling them to a specific review provider.

The future feature should consider:

1. Observable criteria for independent/local business classification.
2. Chain and regional-chain detection without relying on a hardcoded name list.
3. Provider-neutral eligibility/curation state.
4. Manual overrides where automated classification is uncertain.
5. A clear distinction between review-provider availability and business eligibility.
6. How shop owners could eventually claim or request inclusion for their businesses.
7. How curated eligibility interacts with nearby discovery and future search/filtering.

Before implementation:

1. Review the current database schema, coffee shop model, review layer, and existing APIs.
2. Define the independent/local business requirements and observable criteria.
3. Determine what eligibility/curation state should be persisted.
4. Review implications for nearby discovery and future search/filtering.
5. Create and approve the next GitHub Issue.
6. Review the implementation plan before any branch is created or code is written.

---

# Known Blockers

**None.**

Google Places integration is currently implemented through the external review layer. AI processing of external review content remains a future architectural/policy consideration, not a current blocker.

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

**Last Updated:** Phase 2 — Core Application Features (after completion of GitHub Issue #19 and merge of PR #20)
