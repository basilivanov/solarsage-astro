# Wave 14 Calendar Parity Rework 02 Review

Date: 2026-07-08
Reviewed commit: `f8893c0`
Decision: REWORK REQUIRED

## Summary

The Rework 02 direction is correct: replacing fake timers with a fixed `Date`, using a Telegram stub, and removing `networkidle` are all appropriate. However, the required default Playwright command is still not stable.

## Verification Run

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 102.54s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result when run alone after the overloaded parallel attempt: exit 0, 7 files passed, `62 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result with dev server running and no other test processes: exit 1, `10 passed`, `2 failed`.

Failures:

- `[mobile] day tap selects locally...`: timeout waiting for `/day/2026-07-10`.
- `[mobile] moon mode displays backend lunar values...`: `calendar-screen` not found, page stuck at `Авторизация...`.

## Findings

### P0 — Exact default Playwright gate remains red

Evidence:

- The required command still fails without `--workers=1`.
- Error context for mobile moon-mode shows only `Авторизация...`, so auth setup is still not deterministic under default parallel execution.
- Error context for mobile CTA shows the calendar rendered, but URL did not change to `/day/2026-07-10` within 10 seconds.

Required fix:

- Make this exact command pass repeatedly:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

- Since the product path and serial runs are already green, it is acceptable to configure this spec/describe as serial if the report explains why:
  - these are visual/readiness tests against one local Next dev server;
  - they share deterministic auth/runtime setup;
  - serial mode removes non-product worker contention/races.
- If not using serial mode, fix the remaining auth/navigation race directly.

### P1 — CTA navigation assertion remains race-prone on mobile

Evidence:

- The page snapshot after failure shows the calendar is rendered and still on `/calendar`.
- The test waits for URL and clicks the CTA, but the navigation does not happen in the failure case.

Required fix:

- Make the CTA interaction deterministic:
  - ensure the selected summary is visible and the CTA refers to the selected July 10 day;
  - prefer selecting the CTA from within `calendar-selected-summary`, not a broad role query if multiple buttons could match;
  - use `await cta.click()` followed by `await expect(page).toHaveURL(...)`, or otherwise avoid fragile click/navigation promise races.

### P2 — Stale comments mention `page.clock.install`

Evidence:

- `e2e/mock-visual/calendar.spec.ts` module comments still say the test freezes time via `page.clock.install()`, but the implementation now overrides `Date` in `addInitScript`.

Required fix:

- Update comments to match the actual fixed-Date approach.

## Acceptance Gate For Rework 03

Accept only if:

- `pnpm exec tsc --noEmit --pretty false` passes.
- Targeted Vitest suite passes.
- Backend calendar endpoint tests pass.
- Exact default Playwright command passes without manually adding `--workers=1`.
- Report explains whether serial mode was used or which race was fixed.

