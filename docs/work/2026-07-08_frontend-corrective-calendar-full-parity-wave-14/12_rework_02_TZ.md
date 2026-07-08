# TZ: Wave 14 Calendar Parity Rework 02

Date: 2026-07-08
Status: ready for coder
Branch: `main`
Base commit reviewed: `31629ce`
Architect review: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/11_rework_01_review.md`

## Goal

Make the calendar mock-visual Playwright gate deterministic and green under the exact default command from the TZ.

The product UI is close. Do not redesign the calendar in this rework. Focus on test harness/readiness/auth determinism and report accuracy.

## Required Fix

The following command currently fails when run with the normal Playwright worker configuration:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Observed failures:

- Chromium tests timeout at `page.waitForLoadState("networkidle")`, sometimes stuck on `Авторизация...`.
- Mobile `calendar screen renders...` can remain at `data-load-state="loading"`.
- Mobile CTA navigation can timeout waiting for `/day/2026-07-10`.
- The same suite passes with `--workers=1`, which is not enough for acceptance unless the default command also passes.

Fix this properly.

Recommended approach:

1. Add a deterministic mock-visual page setup helper in `e2e/mock-visual/calendar.spec.ts` or a small test-only helper.
2. Before page load, install:
   - `localStorage.setItem("lumen:onboarded", "1")`;
   - a minimal `window.Telegram.WebApp` stub with `initData: ""` so `useTelegramAuth` immediately uses `/api/auth/dev` and does not wait for the external Telegram SDK.
3. Replace `page.waitForLoadState("networkidle")` in the calendar mock-visual spec with semantic readiness waits:
   - wait for `calendar-screen` visible;
   - wait for `data-load-state="ready"` where the test expects ready state;
   - wait for specific route/UI state after CTA navigation.
4. If `expectNoMissingApiFixtures` is the source of `networkidle` flakes, either:
   - add a variant that does not call `networkidle`, or
   - update it safely for mock-visual tests to use short quiet waits and tracker checks instead of network-idle.
5. Do not solve by only changing local instructions to use `--workers=1`.
   - If you choose to configure the spec as serial, the default command must still pass and the report must explain why serial mode is necessary.

## Keep Existing Good Work

Do not regress:

- July 8 oracle scenario.
- SVG `PhaseGlyph` presentation driven by backend `phaseIndex`.
- Sentinel lunar facts matching `LunarFactsService`.
- Typecheck fixes for `CalendarLunarFields.phase` vs `phaseLabel`.
- No frontend lunar date calculations.
- No runtime imports of mocks/demo/MSW.

Do not add more cleanup in this wave.

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

If `localhost:3000` is not running, start local dev server without touching production `3002`, and include the start command in the report.

Do not push or deploy.

## Report

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/13_rework_02_report.md
```

Include:

- root cause of the previous e2e flake;
- exact files changed;
- exact verification results;
- whether dev server was started and on which port;
- any remaining runtime/deploy gap.

## Commit

Commit only relevant files.

Do not stage unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/`
- generated `next-env.d.ts` churn from Next dev server.

## Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Parity Rework 02 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/13_rework_02_report.md. Review: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/11_rework_01_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/12_rework_02_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```

