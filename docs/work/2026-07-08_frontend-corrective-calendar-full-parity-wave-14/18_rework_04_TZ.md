# TZ: Wave 14 Calendar Parity Rework 04

Date: 2026-07-08
Status: ready for coder
Branch: `main`
Base commit reviewed: `dcb63fb`
Architect review: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/17_rework_03_review.md`

## Goal

Finish the calendar mock-visual e2e stabilization so the exact default command is green and repeatable.

This is a test harness / Playwright configuration rework. Do not change calendar product UI unless you first prove the UI code is the cause.

## Current Failure

Architect verification after Rework 03:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

failed with:

```text
Running 12 tests using 2 workers
1 failed
4 did not run
7 passed
```

Failure:

```text
[chromium] calendar screen renders in ready state with month header, grid, lunar strip, and summary
page stayed at "Авторизация..."
```

Important: `test.describe.configure({ mode: "serial" })` is not enough because `chromium` and `mobile` projects still run concurrently under the current config.

## Required Fix

Make the exact command below pass twice in a row with no extra CLI flags:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Acceptable implementation paths:

### Option A: Encode deterministic worker policy in Playwright config

Recommended if you want the smallest reliable fix.

- Make local e2e default to one worker, matching CI.
- Provide an explicit env override for developers who intentionally want parallel e2e, for example `E2E_WORKERS=2`.
- Update comments/module contract in `playwright.config.ts` so the policy is documented.

Expected shape:

```ts
const configuredWorkers = process.env.E2E_WORKERS
  ? Number(process.env.E2E_WORKERS)
  : 1;

export default defineConfig({
  workers: configuredWorkers,
  ...
})
```

Guardrails:

- Validate the env value enough to avoid `NaN`/`0` silently producing odd behavior.
- Keep CI deterministic.
- Do not alter baseURL defaults or product routes.

### Option B: Fix the auth/runtime race directly

Acceptable only if you prove the default two-worker command is stable.

- Investigate why Chromium sometimes stays at `Авторизация...`.
- Keep route interception test-only.
- Keep product code free from mocks.
- Include clear evidence of the root cause and fix in the report.

Do not use this option if the result is just larger arbitrary timeouts.

## Do Not Regress

Keep:

- July 8 oracle scenario.
- SVG `PhaseGlyph`.
- sentinel lunar facts.
- no frontend lunar date calculations.
- no runtime mocks/demo imports.
- no product UI changes unless necessary.
- no push/deploy.

Do not stage unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/`
- generated `next-env.d.ts` churn.

## Required Verification

Run and report exact results:

```bash
git status --short --branch
git diff --check HEAD~1..HEAD
pnpm exec tsc --noEmit --pretty false
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

For both Playwright runs, include the line:

```text
Running 12 tests using N workers
```

If `localhost:3000` is not running, start local dev server without touching production `3002`, and record the command.

## Report

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/19_rework_04_report.md
```

Include:

- files changed;
- chosen option: A worker policy or B race fix;
- exact worker count from both successful Playwright runs;
- exact verification results;
- callback response.

## Commit

Commit only relevant files.

## Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Parity Rework 04 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/19_rework_04_report.md. Review: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/17_rework_03_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/18_rework_04_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```
