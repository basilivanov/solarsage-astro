# Agent Report: Wave 02 — `/calendar` Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-02-calendar-visual-migration`
Base: `f39fd85`

## Summary

Wave 02 migrates the `/calendar` screen presentation toward the mock-preview visual oracle while keeping all data flowing through the real `CalendarPayloadReadModel` from `/api/calendar?month=YYYY-MM`.

No backend contracts were changed. No runtime mocks, MSW, or client-side astrology calculations were introduced.

## Rework 01 Changes (since `35eb10d`)

Based on architect review `02_arch_review.md` and `03_rework_01_TZ.md`:

| Finding | Fix |
|---------|-----|
| E2E moon-mode selector ambiguous (strict mode violation `getByRole("Луна")`) | Added `data-testid="calendar-view-day"` and `data-testid="calendar-view-moon"` to segmented controls; all calendar specs use `getByTestId` |
| Moon-mode assertions date-dependent (TODAY = `new Date()`) | Used `page.clock.install({ time: new Date("2026-07-05T12:00:00Z") })` to freeze time; switched to moon mode first (avoiding `onOpenDay` navigation); assertions check deterministic `2026-07-05` values |
| Ready-state assertion too weak (accepted `lunar-calendar-unavailable` fallback) | Added `data-testid="calendar-month-header"` on month title; ready-state test asserts exact `lunar-calendar-strip` (not fallback); asserts `calendar-view-day` and `calendar-view-moon` visible |
| Branch not handoff-safe (uncommitted `day.spec.ts`) | Included `day.spec.ts` shared-helper import cleanup in commit |
| Report missing Playwright gate evidence | Added exact Playwright result below; removed "Ready to run" and contradictory YooKassa phrasing |
| Shared helper metadata not updated | Updated `route-interception.ts` module map to include `expectNoMissingApiFixtures` |

## Files Changed (since `35eb10d`)

| File | Change |
|------|--------|
| `components/calendar/calendar-screen.tsx` | Added `data-testid="calendar-view-day"`, `data-testid="calendar-view-moon"`, `data-testid="calendar-month-header"` |
| `e2e/mock-visual/calendar.spec.ts` | Fixed moon-mode: use `page.clock.install` to freeze time, switch to moon mode before any day click (avoid `onOpenDay` navigation). Strengthened ready-state: assert `lunar-calendar-strip` not fallback, assert month header and segmented controls |
| `e2e/mock-visual/day.spec.ts` | Import `expectNoMissingApiFixtures` from shared helper (was duplicated locally) |
| `e2e/mock-visual/route-interception.ts` | Updated module map to include `expectNoMissingApiFixtures` in public entrypoints |
| `docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md` | Updated with actual gate results for all commands |

## UI Semantic/Test Contract

| Attribute | Present | Location |
|-----------|---------|----------|
| `data-testid="calendar-screen"` | ✅ | Root div |
| `data-load-state="loading\|ready\|error"` | ✅ | Root div |
| `data-testid="calendar-loading"` | ✅ | Loading state |
| `data-testid="calendar-unavailable"` | ✅ | Error state |
| `data-testid="calendar-grid"` | ✅ | Grid container |
| `data-testid="calendar-day-YYYY-MM-DD"` | ✅ | Each day button |
| `data-testid="calendar-moon-day-YYYY-MM-DD"` | ✅ | Moon mode lunar day |
| `data-testid="calendar-selected-summary"` | ✅ | Bottom summary |
| `data-testid="calendar-month-header"` | ✅ | Month title (new) |
| `data-testid="calendar-view-day"` | ✅ | Дни segment (new) |
| `data-testid="calendar-view-moon"` | ✅ | Луна segment (new) |
| `data-testid="lunar-calendar-strip"` | ✅ | Lunar strip (when data exists) |
| `data-testid="lunar-calendar-unavailable"` | ✅ | Lunar strip (no data) |
| `data-testid="lunar-calendar-selected-detail"` | ✅ | Lunar strip detail panel |
| `aria-pressed` on day buttons | ✅ | Day grid |
| `aria-label` on segmented controls | ✅ | Дни / Луна |
| `disabled` for navigation | ✅ | Month arrows |
| `aria-label` for month nav | ✅ | Previous/Next month |

## Gates Results

### `pnpm exec tsc --noEmit --pretty false`
```
Exit code: 0
```

### `npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/api/calendar.test.ts __tests__/contracts/calendar.test.ts __tests__/lib/calendar.test.ts`
```
Test Files  4 passed (4)
     Tests  53 passed (53)
```

### `npx vitest run`
```
Test Files  84 passed (84)
     Tests  867 passed (867)
```

### `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`
```
8 passed (21.9s)
```

### `git diff --check main..HEAD`
```
Exit code: 0
```

## Backend Contracts Changed

**No.** All changes are frontend-only.

## Runtime Mock / MSW Statement

**No runtime mocks, MSW, mock-preview API routes, or demo data were ported to the product path.**
All calendar data comes through `getMonthCalendar(year, month)` → `CalendarPayloadReadModel`.
Mock fixtures live only in `e2e/mock-visual/` (test-only Playwright route interception).
