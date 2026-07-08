# Wave 14 Calendar Parity Rework 02 Report

Date: 2026-07-08
Branch: `main`
Status: ready for architect review after commit

## Root Cause

The failing default Playwright command was a mock-visual harness issue, not a calendar product regression.

Two mobile tests installed `page.clock` before navigation. `useTelegramAuth` performs dev auth and then waits on a real `setTimeout(500)` before leaving the `Авторизация...` state. With Playwright fake time installed before the app loaded, that timer could fail to advance under parallel workers, leaving the page stuck before `calendar-screen`.

The spec also used `page.waitForLoadState("networkidle")` as a readiness signal, including inside `expectNoMissingApiFixtures`. In Next dev with Telegram/auth/log requests, `networkidle` is not a semantic page-ready signal and made the default-worker harness sensitive to unrelated network timing.

## Files Changed

- `e2e/mock-visual/calendar.spec.ts`
- `e2e/mock-visual/route-interception.ts`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/13_rework_02_report.md`

No product UI files were changed in this rework.

## Fix

- Added a mock-visual page setup helper that installs, before page load:
  - `localStorage.setItem("lumen:onboarded", "1")`
  - a minimal `window.Telegram.WebApp` stub with empty `initData`, forcing the dev-auth path deterministically
  - a test-only fixed `Date`/`Date.now()` for `2026-07-08T12:00:00Z` without fake timers, so app timers keep running
- Replaced calendar spec `networkidle` waits with semantic readiness:
  - `page.goto("/calendar", { waitUntil: "domcontentloaded" })`
  - `calendar-screen` visible
  - `data-load-state="ready"`
- Removed the hidden `networkidle` wait from `expectNoMissingApiFixtures`; it now uses quiet waits plus the missing-request tracker.
- Kept the negative missing-fixture test, but it waits for tracker evidence rather than network-idle.

## Dev Server

`localhost:3000` was already running when this rework started:

```text
LISTEN *:3000 users:(("next-server ..."))
```

I did not start a new dev server and did not touch production `3002` or systemd.

## Verification Results

```bash
git status --short --branch
```

Result: exit 0. Relevant working-tree changes were `e2e/mock-visual/calendar.spec.ts`, `e2e/mock-visual/route-interception.ts`, and this report. Pre-existing untracked files remained: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check
```

Result: exit 0, no output.

```bash
git diff --check HEAD~1..HEAD
```

Result after final commit: exit 0, no output.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0, no output.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.22s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed (24.8s)` under default Playwright workers. No `--workers=1` override was used.

## Remaining Runtime Gap

No deploy and no systemd restart were performed. Real runtime verification against `solarsage-api.service` on port `8000` remains a separate deploy/restart step if that process is still serving an older calendar contract.
