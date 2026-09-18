# Implementation Instructions

The Product Owner has approved the implementation plan.

Implement only the work described in the assigned GitHub Issue and the approved implementation plan.

## Scope Discipline

- Remain strictly within the approved scope.
- Do not begin future issues early.
- Do not introduce unrelated improvements or unnecessary refactors.
- If an out-of-scope improvement is discovered, report it to the Product Owner rather than implementing it.
- If a material product or architectural decision is unclear, stop and ask the Product Owner rather than guessing.

## Implementation

- Review the assigned GitHub Issue and required project documentation before modifying code.
- Implement the approved plan using the repository's existing architecture and conventions.
- Keep changes focused, maintainable, and consistent with the approved scope.
- Add or update tests required to verify the implementation.
- Do not introduce new dependencies unless they are required by the approved issue/plan or explicitly approved by the Product Owner.

## Verification

After implementation:

- Verify the application builds successfully.
- Run all relevant automated tests.
- Run type checking where applicable.
- Run linting where applicable.
- Perform relevant local/manual verification where practical.
- Verify the acceptance criteria are satisfied.
- Check for unintended regressions.
- Do not claim a check passed unless it was actually run.

Report verification results clearly, including:

- passed checks,
- failed checks,
- skipped checks,
- known limitations.

## Final Report

After verification, provide:

- a concise summary of completed work,
- important implementation decisions,
- assumptions made,
- risks or trade-offs discovered,
- limitations or follow-up items,
- complete verification results.

Implementation is ready for Product Owner review only after the above verification and reporting are complete.

## Git Workflow

Agy may perform repository operations required to complete the approved implementation workflow, including:

- creating the approved feature branch,
- committing implementation work,
- pushing to the feature branch,
- creating the Pull Request.

Agy must not:

- merge Pull Requests,
- modify unrelated branches,
- rewrite Git history,
- force push,
- bypass the review process.

## Review Process

1. Product Owner / ChatGPT defines and approves the GitHub Issue.
2. Agy reviews documentation and produces an implementation plan.
3. Product Owner approves the implementation plan.
4. Agy creates the feature branch, implements the work, verifies the implementation, commits, pushes, and opens the Pull Request.
5. CodeRabbit performs automated review.
6. Agy addresses approved review findings and re-verifies.
7. Product Owner performs the final review and merge decision.

Final merge authority belongs to the Product Owner.