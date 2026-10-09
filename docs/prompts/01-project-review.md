Please begin by reviewing the project before making any code changes.

### Repository Preparation

First verify the repository state:

- Confirm the current branch and working tree status.
- Confirm `main` is synchronized with `origin/main`.
- Do not create a feature branch yet.
- Do not modify, create, delete, or rename any project files.

### Required Review

Review the following:

- The assigned GitHub Issue
- `README.md`
- `AGENTS.md`
- `docs/architecture.md`
- `docs/workflow.md`
- `docs/CURRENT_STATE.md`
- For UI/UX-related Issues, also review `docs/ui-design-spec.md`.

Then inspect the existing implementation most relevant to the Issue, including:

- related backend services, schemas, and endpoints;
- related database tables, migrations, RLS policies, indexes, triggers, and RPCs;
- related mobile components, hooks/controllers, navigation, and async state patterns;
- existing tests covering the affected functionality;
- relevant external dependencies or platform capabilities when required by the feature.

Do not assume a new subsystem is necessary when an existing architecture can be extended safely.

### Implementation Plan

After reviewing the repository, present a complete implementation plan containing:

1. **Implementation strategy**
2. **Architecture and data-flow changes**
3. **Database / security changes**
4. **Backend changes**
5. **Mobile changes**
6. **Testing and verification strategy**
7. **Assumptions**
8. **Risks and trade-offs**
9. **Required dependencies**, if any
10. **Expected file changes**
11. **Migration / rollout considerations**, if applicable

For each significant design decision, explain why it fits the existing LOKAL architecture and the Issue scope.

Clearly identify anything uncertain that requires Product Owner judgment.

### Planning Gate

Do not:

- modify any files;
- create a feature branch;
- write implementation code;
- create migrations;
- commit or push;
- open or modify a pull request.

Wait for explicit Product Owner approval of the **final implementation plan**.

Only after approval may implementation begin.