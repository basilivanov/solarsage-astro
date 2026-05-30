---
id: packet-w-test.4
status: active
wave: W-TEST-4
last_review: 2026-05-30
---
# W-TEST-4 — CI integration: test workflow, visual diff artifacts

status: completed
phase: PHASE-TEST
wave: W-TEST-4
modules: M-CI-TESTS

---

## Decision

Integrate all test suites into CI workflow:
1. **Test workflow** — GitHub Actions workflow running all tests
2. **Visual diff artifacts** — upload visual regression diffs as artifacts
3. **Test reporting** — display test results in PR checks

**Why:** CI ensures tests run on every commit. Visual diff artifacts enable review of UI changes. Test reporting provides quick feedback on PR quality.

---

## Acceptance Criteria

- [x] CI workflow runs backend tests (pytest)
- [x] CI workflow runs frontend tests (vitest)
- [x] CI workflow runs E2E tests (Playwright)
- [x] Visual diff artifacts uploaded on failure
- [x] Test results displayed in PR checks

---

## Evidence

- File: `.github/workflows/ci.yml` — CI workflow configuration
- Workflow: Backend tests run on every push
- Workflow: Frontend tests run on every push
- Workflow: E2E tests run on every push
- Workflow: Visual diff artifacts uploaded when tests fail

---

## Negative Tests

- [ ] CI must fail if any test suite fails
- [ ] Visual regression failures must block merge
- [ ] Test artifacts must be accessible for debugging
