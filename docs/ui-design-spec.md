# LOKAL UI Design Specification

**Status:** Approved visual direction; implementation has not started  
**Product phase:** Phase 3 — MVP Polish & Validation  
**Owner:** Product Owner  
**Last reviewed:** 2026-10-10

## Purpose

This document is the visual source of truth for LOKAL's upcoming mobile UI/UX personalization work. It captures the visual direction approved by the Product Owner and maps it to the existing React Native (Expo) application.

The Figma template is a visual reference, not an application to reproduce. LOKAL should borrow its overall design language while keeping LOKAL's existing information architecture, product behavior, and data presentation.

**Figma reference:** [Furniture Co. mobile app — end-to-end e-commerce UI kit](https://www.figma.com/proto/9PGlWgIAoCbfVKgealh5m5/furniture-co.-mobile-app--end-to-end-e-commerce-ui-kit--Community-?node-id=39-107&t=hSiezhnyrt8C0oc5-1)

Do not copy furniture-specific copy, illustrations, product imagery, or commerce flows.

## Approved visual direction

**Mood:** cozy, minimal, modern, local, and lightly editorial.

- Keep most surfaces light and neutral.
- Use caramel tones as LOKAL's brand accents.
- Prefer generous but purposeful whitespace and a clear content hierarchy.
- Use rounded cards and containers, restrained borders, and subtle shadows.
- Use clean, readable sans-serif typography. Editorial or italic emphasis should be occasional, not the default for functional headings.
- Use simple, consistent icons.
- Use coffee-shop imagery only where the existing product already has suitable image data. This issue set does not add an image gallery or image-ingestion capability.

## Color tokens

These are the approved starting values. Implementation must check contrast and consistency with existing styles before applying them broadly. If a value must change for accessibility or platform consistency, Agy must explain the reason in its plan rather than silently inventing a new palette.

| Token | Value | Intended use |
| --- | --- | --- |
| Deep caramel | `#9A6330` | Primary button fill and strong brand actions |
| Warm caramel | `#C9955A` | Brand highlights, accents, and selected-state details |
| Soft neutral | `#F5F6F8` | App canvas and quiet background surfaces |
| White | `#FFFFFF` | Cards, forms, and elevated surfaces |
| Charcoal | `#242424` | Primary text and high-priority content |
| Muted gray | `#686868` | Supporting text and secondary labels |
| Neutral border | `#E8E2D9` | Subtle card and section separation |
| Input border | `#D4C8BE` | Outlined inputs and secondary controls |

### Color usage rules

- Primary buttons use deep caramel (`#9A6330`) with white labels.
- Use the lighter caramel as a restrained accent. When it fills a control, use dark text.
- Secondary actions should use outlined or neutral treatments so they do not compete with the primary action.
- Preserve semantic success, warning, and error colors. Do not replace status meaning with brand caramel.
- Avoid large, saturated brown surfaces that make the overall app feel dark or heavy.

## Typography, spacing, and surfaces

### Typography

- Prefer the existing sans-serif/system font stack for the first implementation.
- Keep shop names, field labels, ratings, distances, and review content quickly scannable.
- Use clear differences between screen titles, section headings, body text, helper text, and metadata.
- Do not add a font dependency without explicit Product Owner approval.

### Spacing

Use a consistent 4-point spacing rhythm. Common starting values are 8, 12, 16, 24, and 32 points. Apply spacing consistently while respecting existing layout constraints and device safe areas.

### Corners, borders, and elevation

- Small controls: approximately 8–10 point corner radius.
- Cards: approximately 12–16 point corner radius.
- Large sheets or prominent surfaces: use a consistent larger radius where the existing layout supports it.
- Prefer subtle borders and shadows over heavy outlines or pronounced elevation.
- Validate values against the existing components before creating new shared abstractions.

### Inputs, buttons, and icons

- Inputs should have clear labels, calm outlined styling, legible placeholder text, visible focus/error states, and existing accessibility labels preserved.
- Primary actions use deep caramel and white text; secondary actions remain visually quieter.
- Loading/disabled states must remain obvious and must not be mistaken for successful completion.
- Keep icons consistent with the current app and dependencies. Do not add an icon package unless the approved issue requires it.

## Map preservation — non-negotiable

LOKAL is map-oriented. The map's job is to help users locate coffee shops, so the current map implementation is explicitly out of scope for visual redesign.

Preserve:

- the existing map rendering and provider behavior;
- markers and their existing selection behavior;
- current-location display, location permissions, and related recovery behavior;
- map region, gestures, selection, and camera movement logic;
- the existing relationship between map selection and shop details.

UI styling may be refined around the map, including existing overlay buttons, the nearby-shop sheet, search input, filter chips, shop cards, and loading/error presentation. Do not change the map itself or its interaction behavior under a UI-personalization issue.

## Screen-by-screen mapping

This mapping targets existing components and behavior. It does not authorize new functionality.

| Screen or area | Existing component(s) | Visual direction | Preserve |
| --- | --- | --- | --- |
| Startup/session restoration | `mobile/App.tsx` | Match loading and connection-error surfaces to the neutral/caramel system | Session restoration, retry, and sign-out behavior |
| Login and registration | `AuthScreen.tsx` | Stronger LOKAL brand area, clean form layout, outlined fields, rounded primary action, balanced whitespace | Current login/register tabs, validation, submission, errors, and auth behavior |
| Map/discovery shell | `LokalMapView.tsx` | Harmonize existing Community/Profile overlays and status banners with the visual system | Map, markers, location, map gestures, and selection logic |
| Nearby discovery/search/filters | `NearbyShopsSheet.tsx` | Consistent search field, filter chips, section headings, counts, shop cards, and empty/loading/error states | Search, filters, sort order, reset behavior, results, and tab behavior |
| Personalized recommendations | `NearbyShopsSheet.tsx` | Reuse nearby-card styles; make recommendation explanations easy to scan | Recommendation algorithm, source data, and insufficient-data semantics |
| Shop details | `ShopDetailCard.tsx` | Clear hierarchy for overview, rating/source information, AI summary, Must Try, and reviews | API contracts, AI calls, favorite/review/share actions, claims, and source separation |
| Profile and saved shops | `ProfileView.tsx` | Minimalist profile card, consistent saved-shop rows and tabs | Existing profile data, favorites, My Claims, logout, and navigation |
| Community feed | `CommunityFeedView.tsx` | Calm review cards, readable author/content hierarchy, consistent actions | Chronological behavior, pagination, review-source rules, sharing, and shop navigation |
| Claim form | `ClaimShopModal.tsx` | Consistent form labels, inputs, primary/secondary actions, and validation states | Claim fields, validation, submission, and status behavior |
| Owner dashboard | `OwnerDashboardModal.tsx` | Consistent cards, metrics, edit form, and section typography | Owner permissions, data, listing updates, and claim status semantics |

### Shop-detail information hierarchy

Within the existing shop-detail experience, prefer this visual order where compatible with the current component and user flow:

1. Shop identity and available location/rating details.
2. AI review summary, clearly labeled as AI-generated.
3. Must Try recommendations.
4. Community and external reviews, with source attribution kept clear.
5. Existing actions and ownership/claim information.

This is a presentation hierarchy, not permission to remove current content or change data-fetching behavior. A large hero image should only be used if valid shop image data already exists.

## Explicit exclusions

Unless a separate GitHub Issue explicitly approves them, do not:

- redesign or replace the map;
- change navigation, information architecture, or existing interactions;
- change backend endpoints, database schema, RLS, provider/provenance rules, curation policy, AI behavior, or recommendation algorithms;
- add password recovery or onboarding screens if they are not already implemented;
- add menus, a photo gallery, coffee-ordering, payments, reservations, or other new product features;
- copy furniture e-commerce flows, text, or assets;
- introduce new dependencies or perform unrelated refactors.

## Implementation sequence

The dataset work in [Issue #49](https://github.com/layugjohann/lokal/issues/49) is a separate validation workstream and must not be mixed with UI implementation.

After the dataset work has proceeded through its own approval workflow, UI work should be split into small issues, in this recommended order:

1. Visual tokens/component patterns and authentication personalization pilot.
2. Discovery overlays, search/filter controls, and nearby shop cards (map unchanged).
3. Shop-detail, AI summary, Must Try, and review presentation.
4. Profile, favorites, community, claim, and owner-dashboard consistency.
5. Cross-screen visual QA and small corrective issues.

Each implementation issue requires its own repository review, Agy plan, explicit Product Owner approval, implementation, automated verification, CodeRabbit review, and Product Owner visual review before merge.

## Definition of visual acceptance

A UI change is ready for Product Owner review when:

- It follows this visual language consistently within the assigned scope.
- The running app is readable and usable on supported device sizes and with safe-area/keyboard behavior.
- Existing navigation, map behavior, authentication, data flows, and user actions remain intact.
- Loading, empty, error, success, and disabled states remain clear and accessible.
- Provider data, first-party reviews, and AI-generated content remain distinguishable.
- No unapproved screens, features, dependencies, API changes, or data-model changes are introduced.
- Required tests, build checks, and TypeScript checks pass.
- The Product Owner has inspected the actual running UI and approved the visual outcome.

Passing automated tests is necessary but does not replace visual QA.
