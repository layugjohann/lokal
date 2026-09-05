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

## GitHub Issue #11 — Maps & Location Integration

**Status:** ✅ Completed

### Completed Work

* Installed and configured Expo SDK 57 compatible `expo-location` (`~57.0.16`) and `react-native-maps` (`1.27.2`) native modules.
* Configured iOS foreground location usage description (`NSLocationWhenInUseUsageDescription`) and Android permissions (`ACCESS_FINE_LOCATION`, `ACCESS_COARSE_LOCATION`) alongside the `expo-location` config plugin in `mobile/app.json`.
* Defined location domain types (`LocationCoordinates`, `LocationPermissionStatus`, `LocationPermissionInfo`, `MapRegion`, `UseLocationResult`) in `mobile/src/types/location.ts`.
* Implemented modular location service abstraction in `mobile/src/services/locationService.ts` normalizing Expo location permissions and coordinate retrieval with balanced accuracy.
* Created custom React hook `useLocation` in `mobile/src/hooks/useLocation.ts` handling foreground permission requests, coordinate retrieval, loading state, non-crashing error state, retry handling, and system settings navigation via `Linking.openSettings()`.
* Built interactive map component `LokalMapView` in `mobile/src/components/LokalMapView.tsx` displaying interactive `react-native-maps` `MapView` centered on user coordinates with camera region animation, fallback default region (Metro Manila), user location marker, and non-blocking state overlays.
* Addressed CodeRabbit review findings for terminal permission denials:
  * Preserved `canAskAgain` metadata from Expo's permission response through the service and hook.
  * When denied with `canAskAgain: true`, provided the standard "Retry" action.
  * When denied with `canAskAgain: false`, designated "Open Settings" as the primary action to redirect the user to device system settings, with a secondary "Check Again" option.
  * Added distinct message and "Grant Permission" handling for the `undetermined` permission state.
* Mounted `LokalMapView` into the root application entry point (`mobile/App.tsx`).
* Verified clean static typing with TypeScript (`npx tsc --noEmit`), Expo bundler export checks across iOS and Android platforms, and backend regression test suite (26 passing tests).

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
| Coffee Shop Discovery / CRUD APIs          | ⏳ Planned  |
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
* Supabase client initialization through `backend/app/core/supabase.py` with lazy loading and HTTPS enforcement.
* Initial database schema migration DDL located at `supabase/migrations/20260811000000_initial_schema.sql`.
* User registration (`POST /api/v1/auth/register`) with email and password.
* User authentication (`POST /api/v1/auth/login`) returning JWT session tokens.
* Non-admin token-scoped user logout (`POST /api/v1/auth/logout`).
* Authenticated user identification (`GET /api/v1/auth/me`) and reusable `get_current_user` dependency for protected routes.
* Automated testing suite executed via Python's standard library `unittest` runner.

CRUD API functionality, Row Level Security (RLS) policies, and mobile auth UI remain outside the scope of Issue #9.

---

# Next Task

The next feature should be defined through the next GitHub Issue and approved implementation plan before development begins.

---

# Known Blockers

**None.**

---

# Session Learnings

The Issue #11 development cycle reinforced the project's AI-assisted engineering workflow.

Key practices established or reinforced:

* Preserving native module permission metadata (such as Expo's `canAskAgain`) enables appropriate UX paths, differentiating between recoverable denials and permanent denials requiring system settings navigation.
* Utilizing built-in platform capabilities (such as React Native's `Linking.openSettings()`) eliminates the need for unapproved third-party dependencies.
* Maintaining a modular mobile architecture (`types`, `services`, `hooks`, `components`) keeps presentation components focused on rendering while encapsulating native APIs and state management.
* Verifying both native export bundles (iOS and Android) alongside TypeScript type-checking ensures cross-platform bundler stability.
* CodeRabbit recommendations regarding edge-case permission handling are evaluated and integrated cleanly within the issue scope.
* `docs/CURRENT_STATE.md` is updated upon feature completion to accurately document repository progress.

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

**Last Updated:** Phase 1 — Project Bootstrapping (after completion of GitHub Issue #11)

