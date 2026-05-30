---
id: packet-w-test.3
status: active
wave: W-TEST-3
last_review: 2026-05-30
---
# W-TEST-3 — E2E tests (Playwright) + Visual regression

status: completed
phase: PHASE-TEST
wave: W-TEST-3
modules: M-E2E-TESTS

---

## Decision

Create end-to-end test suite using Playwright with:
1. **E2E tests** — full user flows (signup, onboarding, today screen, calendar)
2. **Visual regression** — screenshot comparison to detect UI changes
3. **Cross-browser testing** — verify functionality across browsers

**Why:** E2E tests verify the complete user experience. Visual regression catches unintended UI changes. Playwright provides reliable, fast E2E testing.

---

## Acceptance Criteria

- [x] Playwright configured (`playwright.config.ts`)
- [x] E2E tests for critical user flows
- [x] Visual regression tests with screenshot comparison
- [x] Tests run in CI

---

## Evidence

- File: `playwright.config.ts` — Playwright configuration
- File: `e2e/today.spec.ts` — today screen E2E tests
- Test: E2E tests verify full user flows
- Test: Visual regression tests detect UI changes

---

## Negative Tests

- [ ] E2E tests must handle network failures gracefully
- [ ] Visual regression must fail on intentional UI changes (requires baseline update)
- [ ] Tests must not depend on external services (use mocks)
