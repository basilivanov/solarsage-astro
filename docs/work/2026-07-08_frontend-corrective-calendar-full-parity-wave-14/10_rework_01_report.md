# Wave 14 Calendar Parity Rework 01 Report

Date: 2026-07-08
Branch: `main`
Status: ready for architect review after commit

## Files Changed

- `__tests__/components/TodayScreen.test.tsx`
- `__tests__/components/CalendarScreen.test.tsx`
- `components/calendar/phase-glyph.tsx`
- `components/calendar/calendar-screen.tsx`
- `components/calendar/lunar-calendar-strip.tsx`
- `lib/lunar-presentation.ts`
- `e2e/mock-visual/calendar.spec.ts`
- `e2e/mock-visual/fixtures/calendar-2026-07.ts`
- `lib/demo-data.ts` deleted, unused runtime demo file
- `lib/mocks/calendar.ts` deleted, unused runtime mock file
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/*.png`

## Review Findings Resolved

### P0 Typecheck

`TodayScreen` test fixtures now use the v2 lunar contract correctly:

- `phase`: enum key, for example `full_moon`, `waning_gibbous`
- `phaseLabel`: Russian display label, for example `Полнолуние`, `Убывающая Луна`

No contract loosening was introduced.

### P1 Mock-Visual Scenario Date

Mock-visual calendar is aligned to the oracle date `2026-07-08`:

- `generatedAt` is `2026-07-08T06:00:00Z`
- July 8 is `isToday: true`
- Playwright clock freezes to `2026-07-08T12:00:00Z`
- moon-mode selected summary asserts `Сегодня`, `8 июля 2026`, `убыв. серп`, `39%`, `24 лунный день`

### P1 Fixture Lunar Facts

The July 2026 fixture table was replaced with values generated from `apps/api/app/services/lunar_facts_service.py` using `LunarFactsService.facts_for_date(date(2026, 7, day))`.

Added a Playwright sentinel test for:

- `2026-07-05`: `waning_gibbous`, index `5`, `70%`, lunar day `21`
- `2026-07-08`: `waning_crescent`, index `7`, `39%`, lunar day `24`
- `2026-07-11`: `waning_crescent`, index `7`, `12%`, lunar day `27`
- `2026-07-23`: `waxing_gibbous`, index `3`, `64%`, lunar day `9`

### P1 SVG Phase Glyphs

Emoji phase rendering was removed from calendar surfaces. Added `components/calendar/phase-glyph.tsx`, a presentation-only SVG component driven by backend `phaseIndex`.

Updated:

- day-view lunar strip chips
- strip day cells
- selected lunar detail
- moon-mode calendar cells
- moon-mode selected footer
- legend

No frontend date-based lunar calculations were ported from the oracle.

### Product Mock/Demo Guard

The required grep command still found old tracked product files `lib/demo-data.ts` and `lib/mocks/calendar.ts`. They were not imported anywhere, so they were deleted to keep product paths free of runtime mock/demo targets.

## Screenshot Artifacts

Captured from local `http://localhost:3000` with mock-visual route interception and clock `2026-07-08T12:00:00Z`:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-mobile-calendar-top.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-mobile-calendar-lunar.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-tall-calendar-top.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-tall-calendar-lunar.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-desktop-calendar-top.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-desktop-calendar-lunar.png`

Capture command:

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar-capture.tmp.spec.ts --project=chromium
```

Result: exit 0, `1 passed (5.3s)`. Temporary capture spec was deleted and not committed.

## Verification Results

```bash
git status --short --branch
```

Result: exit 0. Relevant tracked changes plus pre-existing untracked `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`.

```bash
git diff --check HEAD~1..HEAD
```

Result: exit 0, no output.

```bash
git diff --check
```

Result: exit 0, no output.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 0, no output.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 4.07s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx
```

Result: exit 0, 6 files passed, `61 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `12 passed (26.1s)`.

```bash
rg -n "lib/mocks/calendar|mocks/calendar|lib/demo-data|USE_FIXTURES|msw|mockServiceWorker|computeMoonPhaseForDay|getLunarDay|getVoidOfCourse" app components lib apps/api e2e __tests__ packages --glob '!node_modules/**'
```

Result: exit 0 with allowed hits only:

- `__tests__/guardrails/no-runtime-mocks.test.ts`
- `e2e/mock-visual/README.md`

## Remaining Runtime Gap

No systemd service was restarted and no deploy was performed. Real runtime verification against the production `solarsage-api.service` on port `8000` remains a separate deploy/restart step if that process is still serving an older `contractVersion=1` calendar response.
