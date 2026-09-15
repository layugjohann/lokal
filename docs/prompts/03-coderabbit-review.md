# 03 — CodeRabbit Review Resolution Prompt

Review and revise the current feature implementation based on the unresolved CodeRabbit findings on the active Pull Request.

---

### Objective

Address actionable CodeRabbit review findings to enhance code quality, correctness, security, and maintainability while strictly preserving the approved feature scope and system architecture.

---

### Instructions

1. **Inspect Active Pull Request**:
   * Retrieve all unresolved CodeRabbit review comments and findings on the active Pull Request using `gh pr view <pr-number> --comments` or the GitHub API.
   * Distinguish actionable code findings from informational comments, warnings, and automated checks (e.g. check summaries) that do not require code modifications.

2. **Evaluate Before Coding**:
   * Treat CodeRabbit's findings as review input, not as instructions to blindly execute.
   * Verify whether each finding is accurate and still exists in the current codebase.

3. **Classify Every Finding**:
   Categorize each finding into one of the following:
   * **Valid and actionable**: The issue is real, affects correctness/security/performance/maintainability, and requires a code fix.
   * **Invalid / not applicable**: The suggestion contradicts project architecture, is factually incorrect, or falls outside the approved issue scope.
   * **Already resolved**: The issue was previously addressed or no longer applies to the current implementation.

4. **Implement Minimal, Scope-Aligned Fixes**:
   * Implement only the fixes for valid actionable findings.
   * Keep changes minimal, focused, and idiomatic.
   * Do not introduce unrelated refactors, styling rewrites, or unapproved features.
   * For findings classified as invalid or already resolved, do not modify code; prepare a concise engineering justification.

5. **Test Coverage & Verification**:
   * When a finding affects behavior, correctness, security, or reliability, update or add automated unit/integration tests to prevent regressions.
   * Run the relevant feature tests.
   * Run the entire existing test suite.
   * Run type checking, linting, and build verification where applicable (e.g., Python `unittest`, TypeScript `tsc --noEmit`, mobile tests).
   * Confirm zero regressions across the codebase.

6. **Diff Inspection & Hygiene**:
   * Inspect the complete `git diff` after making fixes.
   * Ensure only intended review fixes are included.
   * Remove any accidental or debugging artifacts.
   * Do not modify documentation/state-tracking files (such as `docs/CURRENT_STATE.md`) during the review resolution cycle.

7. **Git & Pull Request Workflow**:
   * **Do not create a new feature branch**. Continue using the existing active feature branch.
   * Create a focused commit with a clear message (e.g., `fix: address CodeRabbit review findings for <feature>`).
   * Push the commit to the existing remote branch: `git push origin <feature-branch>`.
   * **Do not merge the Pull Request**.
   * Allow CodeRabbit to re-review the updated Pull Request.

8. **Iterative Review Cycle**:
   * If new actionable findings appear after re-review, repeat the process.
   * The review cycle completes only when all actionable CodeRabbit findings are resolved or justified.

---

### Final Report Requirements

After pushing review fixes, provide a structured report summarizing:

1. **Findings Reviewed**: List every CodeRabbit finding inspected with its file and location.
2. **Classification**:
   * Findings fixed (with description of the minimal fix applied).
   * Findings intentionally skipped (with clear architectural/technical rationale).
3. **Files Changed**: List all modified or created files with brief explanations.
4. **Tests Added/Modified**: Detail any new test cases or updated test suites.
5. **Verification Results**:
   * Feature test results.
   * Full regression test suite results.
   * Type checking, linting, and build verification results.
6. **Git Tracking**:
   * Commit SHA.
   * Confirmation that the existing Pull Request was updated.
   * Reminder that the Pull Request is awaiting Product Owner final review and merge.