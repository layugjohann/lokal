# Zero Cost AI Workflow

This document defines the standard development workflow for the LOKAL project.

The goal of this workflow is to produce high-quality software by combining human decision-making with AI-assisted implementation, automated testing, and AI-powered code review while keeping development costs as close to zero as possible.

---

# Team

The development team consists of the following members:

| Team Member                     | Primary Responsibility                                 |
| ------------------------------- | ------------------------------------------------------ |
| Johann                          | Product vision, feature prioritization, final approval |
| ChatGPT                         | Architecture, planning, technical guidance             |
| Primary AI Implementation Agent | Feature implementation                                 |
| CodeRabbit                      | Automated code review                                  |
| GitHub                          | Source control, Issues, Pull Requests                  |

---

# Guiding Principles

The workflow follows these principles:

* Plan before implementing.
* Keep features small and focused.
* Maintain a single source of truth through GitHub Issues.
* Let AI assist implementation, not replace engineering judgment.
* Test before merging.
* Update documentation when project knowledge changes.
* Prefer consistency over speed.

---

# Feature Development Lifecycle

Every feature follows the same lifecycle.

## 1. Create a GitHub Issue

Each feature begins with a GitHub Issue describing:

* Problem statement
* Goal
* Scope
* Acceptance criteria

No implementation begins without an Issue.

---

## 2. Technical Planning

If necessary, discuss:

* Architecture
* Trade-offs
* Dependencies
* Risks

Large architectural decisions should be made before implementation starts.

---

## 3. Create a Feature Branch

Create a dedicated branch for the feature.

Example:

```text
feature/coffee-shop-search
```

The `main` branch should remain stable.

---

## 4. Implementation

The Primary AI Implementation Agent implements the feature while following:

* AGENTS.md
* architecture.md
* Project coding standards
* GitHub Issue requirements

Implementation should stay within the agreed scope.

---

## 5. Local Testing

Before committing:

* Run unit tests.
* Verify the application builds successfully.
* Confirm the feature behaves as expected.

Known issues should not be ignored.

---

## 6. Commit Changes

Create focused commits with clear messages.

Examples:

```text
feat: add coffee shop search screen

fix: handle empty review responses

refactor: simplify location service
```

Each commit should represent a single logical change.

---

## 7. Push and Open a Pull Request

Push the feature branch and create a Pull Request.

The Pull Request should clearly describe:

* What changed
* Why it changed
* Testing performed
* Any known limitations

---

## 8. Code Review

CodeRabbit reviews the Pull Request.

Review comments should be:

* Addressed
* Discussed
* Or intentionally dismissed with justification

Code review is part of development, not an optional step.

---

## 9. Human Review

Before merging:

* Verify the implementation satisfies the Issue.
* Confirm tests pass.
* Review architecture impact.
* Ensure documentation has been updated if necessary.

---

## 10. Merge

Merge only after review is complete.

Delete the feature branch once it has been merged.

---

# Documentation Workflow

Documentation is considered part of the feature.

Update documentation whenever:

* Architecture changes
* Development workflow changes
* Environment setup changes
* New engineering conventions are introduced

`CURRENT_STATE.md` should be updated at the end of each significant work session.

---

# Testing Philosophy

Testing should provide confidence without becoming unnecessary overhead.

General expectations:

* Add tests for new business logic.
* Update tests when behavior changes.
* Do not remove failing tests to make builds pass.
* Keep tests readable and maintainable.

---

# Continuous Improvement

The workflow is intentionally stable.

Changes should only be made when repeated experience shows that a step no longer provides value or a better approach has been proven.

The objective is continuous improvement through experience, not constant process redesign.

---

# Success Criteria

A feature is considered complete when:

* The GitHub Issue has been satisfied.
* Code has been implemented.
* Tests pass.
* CodeRabbit review has been completed.
* Documentation has been updated where necessary.
* The feature is approved for merge.

---

# Final Principle

The Zero Cost AI Workflow is built around roles, responsibilities, and engineering principles—not specific tools.

AI tools may change over time, but a disciplined engineering process should remain consistent.
