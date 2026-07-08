# Wave 14 Calendar Parity Rework 03 Report

Date: 2026-07-08
Branch: `main`
Status: ready for architect review after commit

## Files Changed

- `e2e/mock-visual/calendar.spec.ts`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/16_rework_03_report.md`

No product UI files were changed.

## Fix

Serial mode was used for the `Mock Visual — /calendar` describe block:

```ts
test.describe.configure({ mode: "serial" })
```

Rationale:

- This spec is a visual/readiness gate against one local Next dev server on `localhost:3000`.
- It installs deterministic mocked auth/runtime state before page load.
- Fresh runs showed the remaining failures were mobile worker contention around auth/readiness, with pages stuck at `Авторизация...`.
- Serializing the calendar mock-visual suite removes the non-product worker race while preserving the exact default command as the acceptance command.

Additional deterministic changes:

- Updated stale module comments that still mentioned `page.clock.install`; the implementation now fixes `Date` via `addInitScript` while keeping browser timers real.
- Scoped the CTA lookup to `calendar-selected-summary`.
- Verified the footer contains `10 июля 2026` before clicking.
- Replaced the click/navigation `Promise.all` race with:
  - `await cta.click()`
  - `await expect(page).toHaveURL(/\/day\/2026-07-10/)`

## Dev Server

`localhost:3000` was already running before this rework:

```text
LISTEN *:3000 users:(("next-server ..."))
```

I did not start a new dev server and did not touch production `3002` or systemd.

## Verification Results

Initial reproduction before the fix:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 1, `8 passed`, `4 failed`; mobile tests were stuck at `Авторизация...` or timed out before/around calendar readiness.

Repeatability checks after the fix:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed (23.8s)`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed (23.3s)`.

Required verification:

```bash
git status --short --branch
```

Result: exit 0. Relevant change: `e2e/mock-visual/calendar.spec.ts`. Pre-existing untracked files remained: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

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

Result: exit 0, `12 passed in 1.24s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
```

Result: exit 0, 7 files passed, `62 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed (27.4s)`.

## Callback

Callback response: `{"ok": true}`.

## Remaining Runtime Gap

No deploy and no systemd restart were performed. Real runtime verification against `solarsage-api.service` on port `8000` remains a separate deploy/restart step if that process is still serving an older calendar contract.
