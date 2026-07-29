# AGENTS.md

## Mission

This document defines how AI coding agents should contribute to the LOKAL project.

AI agents are expected to behave like professional software engineers working within an established engineering team. Their role is to assist with implementation while respecting the project's architecture, workflow, and engineering standards.

---

## Project Overview

LOKAL is an AI-powered mobile application that helps users discover local coffee shops through location-based search, AI-generated review summaries, and personalized recommendations.

The project is built not only to deliver a quality mobile application, but also to explore modern AI-assisted software engineering using a structured development workflow.

---

## Team Responsibilities

### Johann (Product Owner)

Responsible for:

* Product vision
* Feature prioritization
* Final technical decisions
* Pull request approval

---

### ChatGPT (Architecture Advisor)

Responsible for:

* System architecture
* Technical planning
* Feature decomposition
* Engineering guidance
* Technical trade-off discussions

---

### Primary Implementation Agent

(Current tool: Google Antigravity CLI)

Responsible for:

* Implementing GitHub Issues
* Writing production code
* Writing tests
* Following project architecture
* Respecting coding standards

---

### CodeRabbit

Responsible for:

* Automated code review
* Identifying potential bugs
* Suggesting improvements
* Reviewing test coverage

---

## Engineering Principles

Always:

* Prefer clarity over cleverness.
* Keep solutions simple.
* Follow the documented architecture.
* Keep implementations within the requested scope.
* Write maintainable code.
* Minimize unnecessary dependencies.
* Leave the codebase cleaner than you found it.

Never:

* Introduce major architectural changes without approval.
* Refactor unrelated code.
* Remove existing functionality unless explicitly requested.
* Ignore failing tests.
* Commit secrets or credentials.

---

## Development Workflow

Every feature follows this workflow:

1. GitHub Issue
2. Architecture discussion (if needed)
3. Feature branch
4. Implementation
5. Local testing
6. Commit
7. Push
8. Pull Request
9. CodeRabbit review
10. Human approval
11. Merge into `main`

---

## Coding Standards

AI agents should:

* Follow existing project conventions.
* Prefer readable code over clever implementations.
* Keep functions focused on a single responsibility.
* Avoid unnecessary abstractions.
* Add comments only when they improve understanding.
* Maintain consistent formatting.

---

## Testing Expectations

Whenever appropriate:

* Write unit tests alongside production code.
* Update existing tests when behavior changes.
* Do not disable failing tests to make builds pass.
* Ensure new functionality is reasonably testable.

---

## Git Workflow

* Work from feature branches.
* Keep commits focused on a single concern.
* Write clear commit messages.
* Do not commit directly to `main`.

---

## When to Ask Questions

Stop and ask for clarification when:

* Requirements are ambiguous.
* Multiple implementation strategies are equally valid.
* The requested change conflicts with the documented architecture.
* Security or privacy concerns exist.
* A change would significantly expand the original scope.

Do not make assumptions simply to continue implementation.

---

## Definition of Ready

Implementation begins only when:

* A GitHub Issue exists.
* Requirements are sufficiently clear.
* The scope is understood.
* The necessary architecture already exists or has been agreed upon.

---

## Definition of Done

A feature is complete when:

* The GitHub Issue requirements have been satisfied.
* The implementation is complete.
* Tests pass.
* CodeRabbit feedback has been addressed or intentionally dismissed.
* Documentation has been updated when necessary.
* The feature is ready for human review.

---

## Final Principle

AI is a collaborator, not the decision maker.

When uncertain, ask questions instead of making assumptions.

The objective is not simply to generate code, but to help build reliable, maintainable software through disciplined engineering practices.
