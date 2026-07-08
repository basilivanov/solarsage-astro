# Wave 14 Calendar Parity Rework 01 Review

Date: 2026-07-08
Reviewed commit: `31629ce`
Decision: REWORK REQUIRED

## Summary

The rework fixed the previous product-level issues:

- TypeScript typecheck is now clean.
- Calendar fixtures use the July 8 oracle scenario.
- Sentinel lunar fixture values match `LunarFactsService`.
- Calendar phase rendering now uses SVG presentation driven by backend `phaseIndex`, not emoji/date calculations.

The wave is not acceptable yet because the required mock-visual Playwright gate is not stable under the command specified in the TZ.

## Verification Run

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 3.01s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result with dev server running on `localhost:3000`: exit 1.

Failures:

- Chromium `calendar screen renders...`: timed out at `page.waitForLoadState("networkidle")`, snapshot stuck at `Авторизация...`.
- Chromium `day tap selects...`: timed out at `page.waitForLoadState("networkidle")`, snapshot stuck at `Авторизация...`.
- Mobile `calendar screen renders...`: `calendar-screen` stayed `data-load-state="loading"` for the assertion window.
- Mobile `day tap selects...`: timed out waiting for `/day/2026-07-10` navigation.

Control run:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts --workers=1
```

Result: exit 0, `12 passed`.

This proves the product path is close, but the required default test command is flaky/red under parallel workers.

## Findings

### P0 — Required mock-visual e2e command is red under the TZ command

Evidence:

- `e2e/mock-visual/calendar.spec.ts` uses `page.waitForLoadState("networkidle")` after navigation.
- In dev, the app loads Telegram SDK/auth/dev logging/network activity; `networkidle` is not a reliable readiness signal.
- Some workers remain on the auth loading screen, which means test setup is not deterministic.
- The same spec passes with `--workers=1`, so the failure is a harness concurrency/readiness issue, not an acceptable green gate.

Required fix:

- Make the exact TZ command pass:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

- Do not claim `--workers=1` as the acceptance gate unless the spec itself is explicitly configured serial with a clear reason and the default command above passes.
- Prefer a deterministic mock-visual setup:
  - install a no-initData Telegram WebApp stub before page load so `useTelegramAuth` immediately chooses dev auth instead of waiting on the external Telegram SDK;
  - avoid `page.waitForLoadState("networkidle")` as a readiness gate;
  - wait for semantic UI readiness, for example `calendar-screen[data-load-state="ready"]`;
  - keep the missing-fixture tracker assertion, but do not make it depend on `networkidle`.

### P1 — Rework report claims default e2e passed, but reproduction shows it does not

Evidence:

- `10_rework_01_report.md` says `E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts` passed with `12 passed`.
- Fresh reproduction of the same command failed under the default worker configuration.

Required fix:

- Update the next report with the exact command and result after the harness is fixed.
- Include whether the dev server was already running or started by the agent.

### P2 — Runtime mock/demo deletion is broad cleanup, not calendar parity

Evidence:

- `31629ce` deletes `lib/demo-data.ts` and `lib/mocks/calendar.ts`.
- Current import search does not show runtime imports, and guardrail tests pass.
- This is not a blocker by itself, but it is broader than calendar parity and should be explicitly justified as cleanup of dead product-path mock files.

Required fix:

- Do not add more cleanup in this wave.
- In the next report, keep the deletion justification concise:
  - no imports remain;
  - guardrail passes;
  - product paths no longer contain mock/demo payload files.
- If any test/doc starts depending on these files, restore or move the needed data to test-only fixtures.

## Acceptance Gate For Rework 02

Accept only if:

- `pnpm exec tsc --noEmit --pretty false` passes.
- Backend calendar endpoint tests pass.
- Targeted Vitest suite passes.
- Guardrail test passes.
- The exact default mock-visual command passes without adding `--workers=1` manually:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

- New report records exact evidence and does not rely on agent-only claims.

