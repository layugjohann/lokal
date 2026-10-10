# AI-Assisted Engineering Workflow

This document defines the standard engineering workflow for LOKAL.

Every feature follows this process.

## Development Session Checklist

Before starting any feature:

1. `git checkout main`
2. `git pull origin main`
3. `git status` (must be clean)
4. Verify `CURRENT_STATE.md` reflects `main`
5. Review assigned GitHub Issue
6. Review core documentation (`README.md`, `AGENTS.md`, `docs/architecture.md`, `docs/workflow.md`, `docs/CURRENT_STATE.md`)
7. Present implementation plan
8. Wait for Product Owner approval
9. Antigravity (Agy) creates feature branch: `feature/<issue-number>-<short-description>`
10. Begin implementation within approved scope
11. Run automated tests and local verification
12. Commit completed work with clear, conventional commit messages
13. Push feature branch to GitHub
14. Open Pull Request for CodeRabbit review
15. Evaluate and resolve CodeRabbit findings iteratively
16. Product Owner performs final review and approves the Pull Request
17. Product Owner merges the Pull Request and manages branch deletion
18. Agy updates `docs/CURRENT_STATE.md` using the documentation workflow
19. Product Owner synchronizes local `main` and confirms the working tree is clean

---

# Engineering Principles

* GitHub Issues define feature scope, while core project documentation serves as the engineering source of truth.
* Every feature has its own branch.
* Architecture is reviewed before implementation.
* AI proposes a plan before writing code.
* Product Owner approval is mandatory before creating branches or writing code.
* Every issue should leave the project in a working state.
* Documentation evolves alongside the codebase.
* Small, reviewable changes are preferred over large batches of work.
* AI recommendations (from tools like CodeRabbit) are review inputs to be critically evaluated, not blindly executed.

---

# Feature Development Lifecycle

```text
Idea
    │
    ▼
GitHub Issue
    │
    ▼
Architecture / Product Review (if required)
    │
    ▼
Implementation Planning
    │
    ▼
Product Owner Approval
    │
    ▼
Agy Creates Feature Branch
    │
    ▼
Agy Reviews Project Documentation
    │
    ▼
Implementation
    │
    ▼
Automated Testing / Verification
    │
    ▼
Agy Commit
    │
    ▼
Agy Push
    │
    ▼
Agy Opens Pull Request
    │
    ▼
CodeRabbit Review
    │
    ▼
Review Findings Evaluation
    │
    ├── Actionable → Agy Fixes → Tests → Push
    │                         │
    │                         ▼
    │                   CodeRabbit Re-review
    │
    └── No Actionable Findings
                │
                ▼
        Product Owner Final Review
                │
                ▼
             Merge
                │
                ▼
      Synchronize `main`
                │
                ▼
       Update CURRENT_STATE.md
```

---

# Step 1 — GitHub Issue

Every feature begins with a GitHub Issue created or approved by the Product Owner.

Each issue defines the scope of work and should contain:

* Objective
* Background
* Requirements
* Acceptance Criteria
* Out of Scope
* Definition of Done

---

# Step 2 — Architecture Review

Determine whether the feature affects:

* architecture,
* database design,
* APIs,
* security,
* application structure.

If necessary, discuss design decisions with the Product Owner before implementation planning begins.

---

# Step 3 — Implementation Planning

Before touching any code or creating branches, Agy presents an implementation plan covering:

* implementation strategy,
* assumptions,
* risks and trade-offs,
* dependencies,
* expected file changes and tests.

No code is written and no branches are created until the Product Owner approves the plan.

---

# Step 4 — Feature Branch Creation

Once the Product Owner approves the plan, Agy creates a dedicated feature branch.

### Branch Naming Convention

Use:

`feature/<issue-number>-<short-description>`

Examples:

* `feature/3-initialize-fastapi-backend`
* `feature/9-authentication`
* `feature/11-maps-location-integration`
* `feature/13-coffee-shop-crud-api`
* `feature/15-coffee-shop-discovery`

Do not use:

* `feature/issue-2-backend`
* `feature/backend`
* `backend-feature`

All implementation occurs strictly on this branch.

---

# Step 5 — AI Project Review

Before coding, Agy reviews:

* `README.md`
* `AGENTS.md`
* `docs/architecture.md`
* `docs/workflow.md`
* `docs/CURRENT_STATE.md`

For UI/UX-related Issues, also review `docs/ui-design-spec.md`.

This ensures implementation aligns with project standards and conventions.

---

# Step 6 — Implementation

Agy implements **only** the work described in the approved GitHub Issue and plan.

If additional improvements or edge cases are identified outside scope:

* Mention them clearly.
* Explain the benefit.
* Do not implement them without explicit Product Owner approval.

---

# Step 7 — Automated Testing & Verification

Agy verifies that:

* the application builds successfully,
* all relevant tests pass (both new and existing regression tests),
* functionality meets acceptance criteria,
* type checking and linting pass with zero errors,
* no regressions are introduced.

---

# Validation Dataset & Development Seeding Workflow

To safely validate MVP features (Discovery, Reviews, AI Summaries, Must-Try Recommendations, Claims, and Community Feed) without mutating production or violating external provider policies, the repository provides an authoritative validation dataset and CLI tool.

### Authoritative Fixture Source
The single source of truth resides in `backend/app/fixtures/validation_dataset.py`. It defines:
* **23 Shops**: 12 Real Approved Independent Cafes, 6 Synthetic Approved Test Cafes, 3 Excluded Multi-Branch Chains, and 2 Synthetic Pending Curation Cafes.
* **Real Shop Cleanliness**: Real shops contain zero synthetic reviews, zero synthetic menu items, and unpersisted ratings (`NULL`) to comply with Google Places data retention terms.
* **Synthetic Test Fixtures**: 23 synthetic reviews, calibrated ratings, and test menu items exist exclusively on clearly marked `[Test]` synthetic shops.
* **10 Controlled Test Personas**: Predictable auth users under `@lokal.dev` (`scout.juan` through `scout.hannah`, `owner.roberto`, `curator.admin`).

### CLI Management Commands
Managed via `backend/scripts/seed_validation_data.py`:

```bash
# Seed or idempotently verify remote development / local database
python -m backend.scripts.seed_validation_data seed

# Verify record counts across all 6 tables against fixture definitions
python -m backend.scripts.seed_validation_data verify

# Preview scoped deletion of fixture-owned records (dry-run)
python -m backend.scripts.seed_validation_data clean --dry-run

# Scoped deletion of fixture-owned records with confirmation prompt
python -m backend.scripts.seed_validation_data clean

# Export authoritative fixtures into raw SQL seed file
python -m backend.scripts.seed_validation_data export-sql --output supabase/seed.sql
```

### Safety & Idempotency Safeguards
1. **Target Allowlist (Fail-Closed)**: Only explicitly allowlisted hosts (`thustdjwwtkhlhbnuvin.supabase.co`, `127.0.0.1`, `localhost`) under `ENVIRONMENT=development` are permitted. Execution fails closed immediately for any other host or environment without bypass flags.
2. **Read-Before-Write Idempotency**: Existing records are verified against expected fixture payloads. Identical records are left untouched to prevent PostgreSQL `BEFORE UPDATE` triggers from modifying `updated_at` timestamps. Unexpected differences raise an explicit `FixturePayloadConflictError`.
3. **Safe Auth Identity Handling**: User provisioning checks both UUID and email. Existing matching accounts are left untouched without resetting passwords. Identity mismatches raise `IdentityCollisionError`.
4. **Scoped Cleanup**: Deletion targets only exact fixture-owned IDs in strict reverse foreign-key order. User accounts are verified for matching UUID and email before deletion.

### 4-Tier Validation Matrix
1. **Tier 1: Offline Unit & Fixture Tests**
   * Command: `python -m unittest backend/tests/test_validation_dataset.py`
   * Tests coordinates, null ratings for real shops, review isolation, user accounts, claims schema, and exact Haversine distance assertions. Requires no database or network.
2. **Tier 2: Core Regression Tests & Type Checks**
   * Commands:
     * Backend: `python -m unittest discover -s backend/tests`
     * Mobile Tests: `npm test --prefix mobile`
     * Mobile TypeScript: `tsc --noEmit --project mobile/tsconfig.json`
3. **Tier 3: Database-Backed Validation**
   * Commands: `python -m backend.scripts.seed_validation_data seed && python -m backend.scripts.seed_validation_data verify`
   * Validates database triggers, foreign keys, RLS policies, and counts on the development Supabase project. Requires `SUPABASE_SERVICE_ROLE_KEY`.
4. **Tier 4: Provider & AI Integration Checks**
   * Default: Mocked provider tests run as part of Tier 2.
   * Opt-in Live: Live Gemini summarization or Google Places verification when API keys are configured.

---

# Step 8 — Commit

Agy creates clear, focused, single-purpose commits following Conventional Commits.

Examples:

```text
feat: add coffee shop nearby search endpoint
fix: resolve offset pagination tie-breaker in SQL RPC
test: add haversine distance calculation benchmarks
docs: update workflow documentation
```

Keep commits focused and self-contained.

---

# Step 9 — Push

Agy pushes the feature branch to GitHub:

`git push -u origin feature/<issue-number>-<short-description>`

Never commit or push directly to `main`.

---

# Step 10 — Open Pull Request

Agy opens a Pull Request describing:

* what changed,
* why it changed,
* testing and verification performed,
* manual acceptance checks,
* known limitations,
* link to the associated GitHub Issue (`Closes #<issue-number>`).

---

# Step 11 — CodeRabbit Review & Revision Cycle

CodeRabbit automatically reviews the Pull Request.

```text
Implementation
      ↓
Tests
      ↓
Pull Request
      ↓
CodeRabbit
      ↓
Evaluate Findings
      ↓
Fix Valid Findings
      ↓
Run Tests
      ↓
Push
      ↓
CodeRabbit Re-review
      ↓
No Actionable Findings
      ↓
Human Final Review
      ↓
Merge
```

### Review-Resolution Rules:

1. **Evaluate before coding**: Treat CodeRabbit recommendations as review input, not mandatory instructions.
2. **Classify findings**:
   * *Valid and actionable*: Apply the minimal appropriate fix.
   * *Invalid or not applicable*: Do not change code; document the rationale.
   * *Already resolved*: Confirm and document.
3. **Stay on the same branch**: All review fixes are committed and pushed to the **existing feature branch** and **existing Pull Request**. Never create new branches for review comments.
4. **Test after fixes**: Run the test suite and type checking to ensure fixes introduce zero regressions.
5. **Iterative re-review**: CodeRabbit reviews the updated Pull Request. Repeat the cycle until there are no remaining actionable findings.

---

# Step 12 — Human Approval

The Product Owner performs the final review.

Confirm:

* issue requirements are satisfied,
* acceptance criteria are met,
* code quality aligns with project standards,
* CodeRabbit findings have been resolved or justified,
* test suites pass completely.

---

# Step 13 — Merge

The Product Owner merges the Pull Request into `main`.

Agy **never** merges Pull Requests.

---

# Step 14 — Documentation Update (`CURRENT_STATE.md`)

`docs/CURRENT_STATE.md` represents the state of the `main` branch.

It must be updated **only after** a feature has successfully merged into `main`.

Do not update `CURRENT_STATE.md` during an unmerged feature implementation unless explicitly requested.

---

# Feature Complete Checklist

* [ ] Pull Request approved by Product Owner
* [ ] Pull Request merged into `main` by Product Owner
* [ ] Feature branch deleted on remote and local
* [ ] Local `main` checked out and synchronized (`git pull origin main`)
* [ ] `docs/CURRENT_STATE.md` updated to reflect the new state of `main`
* [ ] Documentation updates committed and pushed directly or via docs branch
* [ ] Working tree clean

---

# Team Responsibilities

### Product Owner (Johann)

* Defines product requirements and roadmap.
* Creates and prioritizes GitHub Issues.
* Reviews architecture and trade-offs.
* Approves implementation plans and scope adjustments.
* Performs final Pull Request review.
* Merges Pull Requests into `main`.
* Deletes feature branches after merge.
* Decides when a feature is complete.

### Antigravity (Agy)

* Reviews repository documentation and assigned GitHub Issues.
* Produces detailed implementation plans.
* Waits for Product Owner approval before proceeding.
* Creates the feature branch after plan approval.
* Implements features strictly within the approved scope.
* Runs automated tests, builds, and type checks.
* Creates focused, conventional commits.
* Pushes feature branches to GitHub.
* Opens Pull Requests with comprehensive descriptions.
* Updates `docs/CURRENT_STATE.md` after merge through the documentation workflow.
* Evaluates CodeRabbit review comments critically.
* Fixes valid actionable findings and adds test coverage.
* Pushes review fixes to the active Pull Request.
* Reports implementation, testing, and review results transparently.

Agy must not:
* Implement unapproved scope or speculative features.
* Merge Pull Requests.
* Override Product Owner decisions.
* Make unrelated refactors or formatting sweeps.
* Modify project architecture without PO approval.
* Treat CodeRabbit recommendations as automatically valid without engineering verification.

### CodeRabbit

* Provides automated pull request review.
* Analyzes static quality, security, maintainability, and functional correctness.
* Flags potential edge cases and standards compliance.
* Re-evaluates Pull Requests when new commits are pushed.
* Acts as review input; final decision authority remains with the Product Owner.

