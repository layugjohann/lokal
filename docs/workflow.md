# workflow.md

# Zero Cost AI Workflow

This document defines the standard engineering workflow for LOKAL.

Every feature follows this process.

## Development Session Checklist

Before starting work:

1. Pull the latest changes.
2. Open the project in VS Code.
3. Start Antigravity (`agy`) in a dedicated terminal.
4. Check Antigravity usage (`/usage`).
5. Read `docs/CURRENT_STATE.md`.
6. Review the active GitHub Issue.
7. Verify the correct feature branch is checked out.
8. Begin implementation.

---

# Engineering Principles

* GitHub Issues are the single source of truth.
* Every feature has its own branch.
* Architecture is reviewed before implementation.
* AI proposes a plan before writing code.
* Every issue should leave the project in a working state.
* Documentation evolves alongside the codebase.
* Small, reviewable changes are preferred over large batches of work.

---

# Feature Development Lifecycle

```
Idea
    │
    ▼
GitHub Issue
    │
    ▼
Architecture Review (if required)
    │
    ▼
Product Owner creates Feature Branch
    │
    ▼
AI reviews project documentation
    │
    ▼
AI presents implementation plan
    │
    ▼
Product Owner approval
    │
    ▼
Implementation
    │
    ▼
Local Testing
    │
    ▼
Acceptance Review
    │
    ▼
Update Documentation (if required)
    │
    ▼
Commit
    │
    ▼
Push Branch
    │
    ▼
Open Pull Request
    │
    ▼
CodeRabbit Review
    │
    ▼
Human Review
    │
    ▼
Merge into main
```

---

# Step 1 — GitHub Issue

Every feature begins with a GitHub Issue.

Each issue should contain:

* Objective
* Background
* Requirements
* Acceptance Criteria
* Out of Scope
* Definition of Done

The issue defines the scope of work.

---

# Step 2 — Architecture Review

Determine whether the feature affects:

* architecture,
* database design,
* APIs,
* security,
* application structure.

If necessary, discuss design decisions before implementation begins.

---

# Step 3 — Feature Branch

The Product Owner creates a dedicated feature branch.

Example:

```
feature/issue-7-authentication
```

All implementation occurs on this branch.

---

# Step 4 — AI Project Review

Before coding, the implementation agent reviews:

* README.md
* AGENTS.md
* docs/architecture.md
* docs/workflow.md
* docs/CURRENT_STATE.md

This ensures implementation aligns with project standards.

---

# Step 5 — Implementation Plan

The implementation agent presents:

* implementation strategy,
* assumptions,
* risks,
* dependencies,
* expected file changes.

No code is written until the Product Owner approves the plan.

---

# Step 6 — Implementation

The implementation agent completes only the assigned GitHub Issue.

If additional improvements are identified:

* explain them,
* do not implement them without approval.

---

# Step 7 — Local Testing

Verify:

* application builds,
* tests pass (where applicable),
* functionality works,
* no obvious regressions are introduced.

---

# Step 8 — Acceptance Review

The Product Owner reviews:

* implementation,
* architecture,
* code quality,
* scope compliance.

Only accepted work proceeds to commit.

---

# Step 9 — Documentation

If the issue changes the project state, update documentation.

Possible files include:

* docs/CURRENT_STATE.md
* README.md
* docs/architecture.md
* AGENTS.md
* workflow.md

Documentation should accurately reflect completed work.

---

# Step 10 — Commit

Create a clear, single-purpose commit.

Examples:

```
feat:
fix:
refactor:
docs:
test:
chore:
```

Keep commits focused.

---

# Step 11 — Push

Push the feature branch to GitHub.

Never commit directly to `main`.

---

# Step 12 — Pull Request

Open a Pull Request describing:

* what changed,
* why it changed,
* testing performed,
* screenshots (if applicable),
* known limitations.

---

# Step 13 — Code Review

CodeRabbit reviews the Pull Request.

Review every recommendation.

Accept only suggestions that improve the project.

---

# Step 14 — Human Approval

The Product Owner performs the final review.

Confirm:

* issue requirements satisfied,
* acceptance criteria met,
* documentation updated,
* project builds successfully.

---

# Step 15 — Merge

Merge the Pull Request into `main`.

After merging:

* close the GitHub Issue,
* delete the feature branch,
* begin planning the next issue.

---

## End-of-Session Checklist

Before ending a development session:

- Verify the application still runs.
- Update documentation if needed.
- Review modified files.
- Commit completed work.
- Push the feature branch.
- Update `docs/CURRENT_STATE.md`.
- Record blockers or next steps.

---

# Continuous Improvement

The workflow itself is a living document.

Whenever a completed issue reveals a better process:

1. Discuss the improvement.
2. Update the documentation.
3. Apply the refinement to future work.

The engineering process should evolve alongside the project.
