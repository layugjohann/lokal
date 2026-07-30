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

## Primary AI Implementation Agent (Antigravity CLI)

Responsible for:

* Implementing GitHub Issues
* Refactoring code
* Writing tests
* Updating documentation when appropriate
* Following repository architecture and standards

The implementation agent must remain within the scope of the assigned GitHub Issue.

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

Implementation work always occurs on a dedicated feature branch.

The Product Owner creates and manages branches.

Implementation agents work only on the active feature branch.

Do not:

* create release branches,
* merge branches,
* rewrite Git history,
* force push,
* modify unrelated branches.

---

## Definition of Done

A GitHub Issue is considered complete only when:

- Acceptance criteria are satisfied.
- The application builds successfully.
- Relevant tests pass.
- Documentation is updated (if required).
- Changes remain within the issue scope.
- The Product Owner approves the implementation.

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
* summarize completed work.

If uncertain:

Ask before implementing.

Never guess on architectural or product decisions.

---

# Goal

The objective is not simply to generate code.

The objective is to help build a maintainable, production-quality software project through disciplined engineering practices.
