# Agent Report: Wave 10 — Corrective `/day/[date]` Visual Migration

Date: 2026-07-07
Agent: coding-executor
Branch: `main`

## Summary

Migrated `/day/[date]` presentation toward the 3001 mock-preview oracle while preserving real API data flow. Removed the intermediate `DayOverviewCard` from the top, introduced a compact `DaySummaryCard` using real `payload.dayStatus`, `calendarLunar`, `topFlags`, and `planetInfluences`, and reordered sections per oracle.

## Files Changed

| File | Change |
|------|--------|
| `components/today/today-screen.tsx` | Reordered layout: headline → access card → DaySummaryCard → practical list → reading → why → week strip. Removed DayOverviewCard, DayChart, DayEnergyMeter from default rendering. |
| `components/today/day-summary-card.tsx` | Rewritten to compact oracle style using real API data only (no local astrology). Accepts `topFlags` and `planetInfluences` instead of `sphereScores`. |
| `__tests__/components/TodayScreen.test.tsx` | Updated assertions: `day-summary-card` replaces `day-overview-card`, removed `day-chart`/`day-energy-meter` assertions, added `practical-list`/`day-reading`. Updated DaySummaryCard standalone test for new props. |

## Architectural Choices

1. **DaySummaryCard** kept presentation-only: status emoji/label/line from `dayStatus`, lunar data from `calendarLunar`, top advice from `topFlags[0]`, top planet from `planetInfluences[0]`. No `computeMoonPhase`, `getAllRetrogrades`, or other local astrology.
2. **Headline** moved from standalone centered block to subtle inline format.
3. **DayChart** and **DayEnergyMeter** removed from default layout to match oracle first-viewport density. They remain available as components for future use.
4. **`DayOverviewCard`** file retained but no longer imported.

## Tests

| Suite | Result |
|-------|--------|
| `npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/lib/adapt-payload.test.ts __tests__/guardrails/no-runtime-mocks.test.ts` | 37 passed |
| `npx vitest run` (full) | 896 passed (1 pre-existing YooKassa guardrail fails) |
| `npx tsc --noEmit --pretty false` | Clean |

## Commands Run

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
# → 37 passed

npx tsc --noEmit --pretty false
# → exit 0
```

## Known Gaps

- Playwright e2e not run (requires local dev server on port 3000/3002). Mock-visual day spec will need `day-summary-card` testid update in a follow-up.
- `day-chart` and `day-energy-meter` are no longer rendered in default layout. They remain importable components.

## Push

Push attempted: No
Push: NOT_ATTEMPTED
