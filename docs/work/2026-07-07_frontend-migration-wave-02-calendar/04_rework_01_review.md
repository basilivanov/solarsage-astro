# Rework 01 Review: Frontend Migration Wave 02 Calendar

Date: 2026-07-07
Reviewer: architect
Branch reviewed: `wave-02-calendar-visual-migration`
Commit reviewed: `4d7eb42`
Status: `REWORK_REQUIRED`

## Summary

Rework 01 fixed the code-level blockers from `02_arch_review.md`.

Fresh architect verification shows the required product and e2e gates now pass:

- `git diff --check main..HEAD`: passed.
- `git diff --check`: passed.
- `pnpm exec tsc --noEmit --pretty false`: passed.
- Targeted calendar Vitest: passed, `4` files / `53` tests.
- Full Vitest: passed, `84` files / `867` tests.
- Mock visual Playwright: passed, `8` tests / `8` passed.

The remaining issue is handoff/report hygiene: `01_agent_report.md` still omits one required gate entry, and two comments no longer match the implemented deterministic clock-freeze/shared-helper approach.

## Findings

### Critical

None.

### Important

1. `01_agent_report.md` is still missing the required plain `git diff --check` gate.

Evidence:

- `03_rework_01_TZ.md` required both:
  - `git diff --check main..HEAD`
  - `git diff --check`
- `01_agent_report.md` reports only `git diff --check main..HEAD`.

Required fix:

Add a separate report subsection for:

```bash
git diff --check
```

with the actual fresh result.

### Minor

1. `calendar.spec.ts` metadata says date-dependent assertions explicitly select the target day, but the implementation uses `page.clock.install()`.

Required fix:

Update comments/module contract to say the test freezes browser time to `2026-07-05` before app init.

2. `day.spec.ts` dependency comment still names `MissingRequestsTracker`, while the file now imports `expectNoMissingApiFixtures` directly.

Required fix:

Update the dependency comment to include `expectNoMissingApiFixtures`.

## Decision

`REWORK_REQUIRED`

Apply `05_rework_02_TZ.md`. This is a small handoff cleanup; do not change product behavior.
