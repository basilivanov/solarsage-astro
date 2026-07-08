# TZ: Wave 14 Calendar Parity Rework 03

Date: 2026-07-08
Status: ready for coder
Branch: `main`
Base commit reviewed: `f8893c0`
Architect review: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/14_rework_02_review.md`

## Goal

Finish stabilizing `e2e/mock-visual/calendar.spec.ts` so the exact default command is green and repeatable.

Do not change calendar product UI in this rework unless absolutely necessary. This is a test harness/readiness rework.

## Current Failure

With local dev server running:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

failed with:

- `10 passed`, `2 failed`;
- mobile CTA test timed out waiting for `/day/2026-07-10`;
- mobile moon-mode test stayed at `Авторизация...`.

The same product path has passed in serial runs, so this is a default-worker harness issue.

## Required Fix

Make the exact command above pass under default Playwright settings.

Acceptable options:

1. Configure the calendar mock-visual describe/spec as serial, if this is the simplest honest fix.
   - This is acceptable because these are visual/readiness tests against one local Next dev server and deterministic mocked auth/runtime.
   - The default command must still pass.
   - The report must explicitly say serial mode was chosen and why.

2. Or remove the remaining worker race directly.
   - Keep the Telegram stub/fixed Date approach.
   - Ensure every test waits for semantic readiness.
   - Ensure CTA click/navigation is scoped and deterministic.

For the CTA test:

- Scope the CTA to `calendar-selected-summary` so the clicked button is definitely the selected-day footer button.
- Verify the footer says `10 июля 2026` before clicking.
- Prefer:

```ts
await cta.click()
await expect(page).toHaveURL(/\/day\/2026-07-10/)
```

over a fragile Promise race if needed.

Also update stale comments that still mention `page.clock.install`; the implementation uses fixed `Date` via `addInitScript`.

## Do Not Regress

Keep:

- July 8 oracle scenario.
- SVG `PhaseGlyph`.
- sentinel lunar facts.
- no frontend lunar date calculations.
- no runtime mocks/demo imports.
- no product UI changes unless necessary.

Do not push/deploy.

## Required Verification

Run and report exact results:

```bash
git status --short --branch
git diff --check HEAD~1..HEAD
pnpm exec tsc --noEmit --pretty false
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

If `localhost:3000` is not running, start local dev server without touching production `3002`, and record the command.

## Report

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/16_rework_03_report.md
```

Include:

- files changed;
- whether serial mode was used or the race was fixed another way;
- exact verification results;
- callback response.

## Commit

Commit only relevant files.

Do not stage unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/`
- generated `next-env.d.ts` churn.

## Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Parity Rework 03 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/16_rework_03_report.md. Review: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/14_rework_02_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/15_rework_03_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```

