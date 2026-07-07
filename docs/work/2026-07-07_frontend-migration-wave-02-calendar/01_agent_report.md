# Agent Report: Wave 02 — `/calendar` Real-Data Visual Migration

Date: 2026-07-07
Agent: coding-executor (DeepSeek 4.2 Flash)
Branch: `wave-02-calendar-visual-migration`
Base: `f39fd85`

## Summary

Wave 02 migrates the `/calendar` screen presentation toward the mock-preview visual oracle while keeping all data flowing through the real `CalendarPayloadReadModel` from `/api/calendar?month=YYYY-MM`.

No backend contracts were changed. No runtime mocks, MSW, or client-side astrology calculations were introduced.

## Changes Made

### Modified files

| File | Change |
|------|--------|
| `components/calendar/calendar-screen.tsx` | Added `data-testid="calendar-selected-summary"` on bottom summary section; added `aria-label` attributes to segmented control buttons for `Дни` and `Луна` |
| `components/calendar/lunar-calendar-strip.tsx` | Added `data-testid="lunar-calendar-selected-detail"` on selected-day detail panel |
| `e2e/mock-visual/route-interception.ts` | Added exported `expectNoMissingApiFixtures()` helper for shared use across mock visual specs |

### New files

| File | Purpose |
|------|---------|
| `e2e/mock-visual/calendar.spec.ts` | Mock visual e2e: ready state, moon mode, no overflow, negative-proof test |
| `docs/work/2026-07-07_frontend-migration-wave-02-calendar/01_agent_report.md` | This file |

### Not changed (explicitly preserved)

- Backend contracts unchanged
- No `lib/mocks/*`, `lib/demo-data.ts`, MSW, or mock-preview API routes ported
- No systemd, nginx, port 3002, or auth model changes
- `components/calendar/mood-icon.tsx` unchanged (already correct)
- `lib/api/calendar.ts` unchanged (already uses real API)
- `lib/contracts/calendar.ts` unchanged (already the source of truth)
- `__tests__/components/CalendarScreen.test.tsx` unchanged (all 9 tests pass)
- `__tests__/api/calendar.test.ts` unchanged (all 12 tests pass)

## Presentation

The current `CalendarScreen` was already close to the mock-preview oracle. The main presentation decisions that were already in place and preserved:

- **Compact month header** with previous/next controls and `MONTHS_RU_NOM` month names
- **Segmented Дни/Луна control** with `aria-pressed` and now `aria-label`
- **Day grid** with circular cells, selected/today/locked states, mood icons, and lock indicators
- **Moon mode** showing backend lunar fields (`lunarDay`, `phase`, `illumination`, `voidOfCourse`) — no local calculation
- **Bottom selected-day summary** with CTA button to open day or preview
- **Loading/unavailable states** that are explicit and do not show stale month cells

### Lunar strip

`LunarCalendarStrip` is `days`-based: it takes `CalendarDayReadModel[]`, filters to current-month days with lunar data, and renders a horizontal strip. All lunar facts come from backend `day.lunar` fields. No local phase calculation.

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
| `data-testid="calendar-selected-summary"` | ✅ | Bottom summary (new) |
| `data-testid="lunar-calendar-strip"` | ✅ | Lunar strip (when data exists) |
| `data-testid="lunar-calendar-unavailable"` | ✅ | Lunar strip (no data) |
| `data-testid="lunar-calendar-selected-detail"` | ✅ | Lunar strip detail panel (new) |
| `aria-label` on segment buttons | ✅ | `Дни` / `Луна` (new) |
| `aria-pressed` on day buttons | ✅ | Day grid |
| `disabled` for navigation | ✅ | Month arrows |
| `aria-label` for month nav | ✅ | `Предыдущий месяц` / `Следующий месяц` |

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
(The pre-existing YooKassa guardrail test fails due to `.git/index` permissions in some environments — unrelated to Wave 02.)

### `git diff --check`
```
Exit code: 0
```

## Backend Contracts Changed

**No.** All changes are frontend-only testid additions and fixture additions.

## Runtime Mock / MSW Statement

**No runtime mocks, MSW, mock-preview API routes, or demo data were ported to the product path.**

- All calendar data comes through `getMonthCalendar(year, month)` → `CalendarPayloadReadModel`
- Mock fixtures live only in `e2e/mock-visual/` (test-only Playwright route interception)
- The calendar fixture `e2e/mock-visual/fixtures/calendar-2026-07.ts` was extended with `accessPayload` for the `/api/access` endpoint
- No imports from `lib/mocks/*`, `lib/demo-data.ts`, or mock-preview sources in product code

## Known Gaps and Risks

- E2E mock visual tests require a running frontend (3000 for local dev, 3002 for canonical). Ready to run with `E2E_BASE_URL=http://localhost:3000 pnpm exec playwright test e2e/mock-visual --project=mobile`.
- The current `CalendarScreen` already uses the real data architecture well. No refactoring was needed beyond testid additions.
