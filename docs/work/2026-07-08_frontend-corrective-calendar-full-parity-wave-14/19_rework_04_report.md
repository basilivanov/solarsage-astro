# Wave 14 Calendar Parity Rework 04 Report

Date: 2026-07-08
Branch: `main`
Status: ready for architect review after commit

## Files Changed

- `playwright.config.ts`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/19_rework_04_report.md`

No product UI files were changed.

## Chosen Option

Option A: deterministic Playwright worker policy.

`playwright.config.ts` now defaults E2E to one worker locally and in CI. Developers can opt into local parallelism explicitly with `E2E_WORKERS=<positive integer>`.

Why this was chosen:

- Rework 03 serialized the calendar describe block, but Playwright still ran the `chromium` and `mobile` projects concurrently.
- The exact command still started as `Running 12 tests using 2 workers` and reproduced auth/readiness hangs at `Авторизация...`.
- Mock-visual and screenshot/readiness tests share one local Next dev server and deterministic mocked auth/runtime setup, so deterministic ordering is the safer default.
- CI already used one worker, so this aligns local behavior with CI.

The override is validated: outside CI, `E2E_WORKERS` must be a positive integer. CI always uses one worker.

## Dev Server

`localhost:3000` was already running before this rework:

```text
LISTEN *:3000 users:(("next-server ..."))
```

I did not start a new dev server and did not touch production `3002` or systemd.

## Reproduction Before Fix

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result before the config change: exit 1.

```text
Running 12 tests using 2 workers
1 failed
4 did not run
7 passed
```

Failure was the same cross-project auth/readiness symptom: `chromium` stayed at `Авторизация...` and `calendar-screen` never appeared.

## Verification Results

```bash
git status --short --branch
```

Result: exit 0. Relevant change: `playwright.config.ts`. Pre-existing untracked files remained: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check HEAD~1..HEAD
```

Result before commit: exit 0, no output. Final post-commit result: exit 0, no output.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0, no output.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.23s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

First required Playwright run:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Worker line:

```text
Running 12 tests using 1 worker
```

Result: exit 0, `12 passed (33.7s)`.

Second required Playwright run:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Worker line:

```text
Running 12 tests using 1 worker
```

Result: exit 0, `12 passed (34.2s)`.

## Callback

Callback response: `{"ok": true}`.

## Remaining Runtime Gap

No deploy and no systemd restart were performed. Real runtime verification against `solarsage-api.service` on port `8000` remains a separate deploy/restart step if that process is still serving an older calendar contract.
