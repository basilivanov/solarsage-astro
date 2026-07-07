# Architect Review: Wave 10 — Corrective `/day/[date]` Visual Migration

Date: 2026-07-07
Branch: `main`
Reviewed commit: `1b323ef`
Status: REJECTED

## Summary

Wave 10 moved `/day/[date]` closer to the 3001 visual oracle, but it is not acceptable yet.
The current implementation still does not reproduce the 3001 day screen as a full scrollable composition.
The first viewport changed, but below-fold structure and proof are incomplete.

The target is not "old main with a new summary card". The target is the 3001 mock-preview day UI, wired to real main contracts and adapters.

## Findings

### P1 — Screen composition still does not match the 3001 oracle

`components/today/today-screen.tsx:161-230`

The current order is:

1. date header
2. `payload.headline`
3. access/trial card
4. `YesterdayEchoLoader`
5. `DaySummaryCard`
6. `TodayPracticalList`
7. important/notes/reading/why/week

The 3001 oracle order is:

1. date header
2. trial/access card
3. evening/check-in reminder
4. compact day summary
5. "Конкретно сегодня" sphere advice table
6. chart when real chart data exists
7. reading
8. why
9. week strip
10. astro/history/disclaimer bottom area

The visible 3001 screenshot has no standalone headline between the date and trial card.
Leaving the headline there keeps the Telegram view visually different from the oracle.

### P1 — "Конкретно сегодня" was not ported from the oracle component

`components/today/today-practical-list.tsx`

The current `TodayPracticalList` is a card list derived from top flags, top sphere scores, and notes.
The 3001 oracle has a denser section with a divider title, good/caution counters, a "все 12 сфер" control, rows for spheres, icons, advice text, and verdict dots.

This section is one of the most visible below-fold differences. It must be ported as presentation, but not as mock astrology logic.
Do not copy `computeMoonPhase`, `getAllRetrogrades`, `getVoidOfCourse`, or local static astrology from the mock-preview.
Build the section from real main data: `payload.sphereScores`, `payload.topFlags`, and `payload.notes`.

### P1 — Below-fold evidence gate is still missing

`docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/01_agent_report.md`
`e2e/mock-visual/day.spec.ts`

The report still says Playwright was not run and that the mock-visual day spec needs a follow-up update.
The current e2e diff only checks that internal scroll height is greater than 100 and then asserts `week-strip` visibility.
That does not prove the full migrated screen matches 3001 below the first viewport.

Wave 10 must produce its own artifacts, not overwrite Wave 09 evidence:

- 3001 top/middle/bottom screenshots
- 3002 or local main preview top/middle/bottom screenshots
- JSON summary with route, scroll positions, section order, and screenshot paths

The evidence must include at least the below-fold sections: `day-summary-card`, concrete advice, chart-or-graceful-chart-absence, reading, why, week strip, bottom disclaimer/history area.

### P2 — Module contract and imports are stale

`components/today/today-screen.tsx:7-11`
`components/today/today-screen.tsx:40`
`components/today/today-screen.tsx:47`
`components/today/day-summary-card.tsx:4`

The module contract still says the screen composes `DayOverviewCard`, chart, and energy meter, but the implementation no longer does.
`DayChart`, `AdaptedTopFlag`, and `SphereScore` are imported but unused.

This is small, but it violates the internal module-contract discipline and makes future reviews harder.

### P2 — Generated `next-env.d.ts` must not be committed as part of this wave

`next-env.d.ts`

The current working tree has:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next-prod/types/routes.d.ts";
```

This is a build artifact side effect, not a product change. Restore it before final commit unless there is a deliberate architecture decision and matching docs.

## Required Rework

Implement the rework in `03_rework_01_TZ.md`.

Do not request accept until:

1. `/day/2026-07-05` visually follows the 3001 oracle through internal-scroll top/middle/bottom.
2. Production/runtime code has no mock astrology imports.
3. Tests and evidence are updated.
4. `next-env.d.ts` is clean or intentionally justified.
