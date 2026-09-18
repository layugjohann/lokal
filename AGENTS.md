# AGENTS.md

# AI Engineering Guidelines

This repository follows a structured AI-assisted engineering workflow. AI agents are expected to operate as members of the engineering team, not as autonomous decision makers.

The Product Owner is the final authority on all architectural, implementation, and product decisions.

---

# Team Roles

## Product Owner (Johann)

Responsible for:

* Product vision
* Feature prioritization
* GitHub Issues
* Architecture approval
* Final code review
* Pull request approval
* Merge decisions

---

## ChatGPT (Architecture Advisor)

Responsible for:

* System architecture
* Technical planning
* Design reviews
* Engineering workflow improvements
* Technology recommendations
* Architectural trade-off discussions

ChatGPT does **not** directly implement production code unless explicitly requested.

---

## Primary AI Implementation Agent (Antigravity CLI / Agy)

Responsible for:

* Reviewing assigned GitHub Issues and project documentation
* Formulating implementation plans
* Implementing approved GitHub Issues
* Creating feature branches after Product Owner approval
* Writing tests and running verification
* Committing and pushing implementation work to the feature branch
* Opening Pull Requests after implementation is verified
* Evaluating and resolving valid CodeRabbit findings on the active Pull Request
* Updating documentation when assigned through the documentation workflow
* Reporting completed work, assumptions, risks, trade-offs, and limitations

Agy must remain strictly within the scope of the GitHub Issue and Product Owner-approved implementation plan.

Agy must not:

* merge Pull Requests,
* override Product Owner decisions,
* implement unapproved scope,
* rewrite Git history,
* force push,
* modify unrelated branches.

---

## CodeRabbit

Responsible for:

* Automated pull request review
* Code quality suggestions
* Static analysis
* Best practice recommendations

CodeRabbit provides recommendations only.

Final approval belongs to the Product Owner.

---

# Source of Truth

GitHub Issues define the scope of work for each task. The core project documentation serves as the architectural and engineering source of truth.

Before implementing any work, review:

* README.md
* AGENTS.md
* docs/architecture.md
* docs/workflow.md
* docs/CURRENT_STATE.md

If documentation conflicts with implementation, documentation takes precedence until the Product Owner decides otherwise.

---

# Implementation Planning

Before modifying any files, the implementation agent must:

1. Review the assigned GitHub Issue.
2. Explain the implementation plan.
3. Identify assumptions.
4. Highlight potential risks or trade-offs.
5. Wait for Product Owner approval.

Do not begin implementation until the plan has been approved.

---

# Scope Discipline

Implement **only** the work described in the assigned GitHub Issue.

Do not:

* begin future issues early,
* introduce unrelated improvements,
* perform unnecessary refactors.

If a potential improvement is discovered outside the issue scope:

1. Mention it.
2. Explain the benefit.
3. Wait for Product Owner approval before implementing it.

---

# Documentation Responsibilities

When an issue changes the project's state, update documentation as appropriate.

Possible updates include:

* docs/CURRENT_STATE.md
* README.md
* docs/architecture.md
* docs/workflow.md

Documentation updates must:

* accurately reflect the implementation,
* remain within the issue scope,
* avoid speculative future work.

---

# Dependency Policy

Do not introduce:

* frameworks
* SDKs
* AI tools
* npm packages
* Python packages
* third-party services

unless they are:

1. Required by the GitHub Issue, or
2. Explicitly approved by the Product Owner.

Every dependency should have a clear engineering justification.

---

# Git Workflow

Implementation work occurs on a dedicated feature branch.

After the Product Owner approves Agy's implementation plan, Agy is authorized to:

* create the feature branch,
* implement the approved work,
* commit focused changes,
* push the feature branch,
* open the Pull Request.

Agy must never:

* merge Pull Requests,
* rewrite Git history,
* force push,
* modify unrelated branches,
* bypass the review process.

The Product Owner retains final authority over the merge and completion decision.

## Post-Implementation Verification

After implementation, Agy must:

1. Verify the application builds successfully.
2. Run all relevant automated tests.
3. Run type checking where applicable.
4. Run linting where applicable.
5. Perform relevant local/manual verification where practical.
6. Confirm the implementation satisfies the approved acceptance criteria.
7. Check for unintended regressions.
8. Summarize the completed work.
9. Report assumptions made.
10. Report risks, trade-offs, or limitations discovered.

Agy must not claim successful verification without actually performing it.

Verification results must clearly distinguish:

* passed checks,
* failed checks,
* skipped checks,
* known limitations.

## Definition of Done

Implementation is considered ready for Product Owner review when:

- Approved scope has been implemented.
- Acceptance criteria have been addressed.
- The application builds successfully.
- Relevant tests pass.
- Relevant type checks and linting pass.
- Manual verification has been performed where appropriate.
- No known unintended regressions remain.
- Documentation has been updated when required by the approved scope.
- Assumptions and limitations have been reported.
- Changes remain within the approved GitHub Issue and implementation plan.

Implementation readiness does **not** mean the issue is complete.

The Product Owner determines final completion after reviewing the implementation and managing the repository workflow.

Implementation alone does not mean the issue is complete.

---

## Decision Transparency

When making significant implementation decisions, explain:

- Why the approach was chosen.
- Alternative approaches considered (if applicable).
- Any trade-offs.
- Assumptions made.

The goal is to keep architectural reasoning visible to the Product Owner.

---

# Code Standards

Write code that is:

* readable
* maintainable
* modular
* well documented when appropriate

Prefer:

* small functions
* descriptive naming
* composition over duplication
* simple solutions over clever solutions

Avoid unnecessary complexity.

---

# Testing

Every completed issue should leave the project in a working state.

Where appropriate:

* run relevant tests,
* verify the application builds,
* verify new functionality,
* report any limitations discovered.

Do not claim that code works without verification.

---

# Communication

Communicate like a software engineer working within a professional team.

When presenting work:

* explain important decisions,
* mention assumptions,
* identify risks,
* summarize completed work,
* provide verification results.

If uncertain about a material product or architectural decision, ask before implementing.

Never guess on architectural or product decisions.

---

# Goal

The objective is not simply to generate code.

The objective is to help build a maintainable, production-quality software project through disciplined AI-assisted engineering while keeping engineering judgment and repository control with the Product Owner.
