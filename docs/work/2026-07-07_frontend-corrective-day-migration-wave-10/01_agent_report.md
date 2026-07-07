# Agent Report: Wave 10 — Rework 01 `/day/[date]` Oracle Composition

Date: 2026-07-07
Agent: coding-executor
Branch: `main`
Route under review: `/day/2026-07-05`

## Summary

Reworked the main `/day/[date]` screen to follow the 3001 mock-preview composition as a full internally scrollable screen while keeping production data flow on `useDay`, `adaptTodayPayload`, calendar/access contracts, and route-intercepted real-shaped API payloads in tests.

The standalone `payload.headline` block was removed from the top visible flow. The accessible ready-state order is now:

1. `day-header`
2. `access-card`
3. `evening-checkin-reminder`
4. `day-summary-card`
5. `concrete-day-advice`
6. `day-chart` or `day-chart-unavailable`
7. `day-reading`
8. `why-expanded`
9. `week-strip`
10. `today-bottom-disclaimer`

## Product Files Changed

| File | Change |
|------|--------|
| `components/today/today-screen.tsx` | Reordered ready-state layout, removed standalone top headline, added check-in reminder wrapper, wired concrete advice, restored chart/unavailable rendering from `payload.dayChart`, added bottom disclaimer selector, cleaned stale imports/contract. |
| `components/today/concrete-day-advice.tsx` | New oracle-style "Конкретно сегодня" section built from `payload.sphereScores`, `payload.topFlags`, and `payload.notes`; no local astrology calculations or mock-preview imports. |
| `components/today/day-reading.tsx` | Aligned public selector to `data-testid="day-reading"`. |
| `components/today/why-expanded.tsx` | Added required `data-testid="why-expanded"`. |
| `lib/display/sphere-labels.ts` | Added legacy key labels for `relationships`, `career`, and `rest` so advice rows still use `getSphereLabel`. |

## Test Files Changed

| File | Change |
|------|--------|
| `__tests__/components/TodayScreen.test.tsx` | Added RED/GREEN coverage for oracle section order, removed standalone headline assertion, check-in reminder, `concrete-day-advice`, chart unavailable/available, and bottom disclaimer. |
| `e2e/mock-visual/day.spec.ts` | Added ready-state section-order checks, `concrete-day-advice` assertions, chart unavailable assertion, internal scroll top/middle/bottom reachability, and `day-reading` selector update. |

## Runtime Mock Guardrail

Production/runtime code does not import `lib/mocks`, `lib/demo-data`, `/opt/solarsage-astro-mock-preview`, or mock-preview astrology helpers. The new concrete advice component does not copy or call `computeMoonPhase`, `getAllRetrogrades`, `getVoidOfCourse`, or demo `NATAL_*` data.

## Tests Run

| Command | Result |
|---------|--------|
| `npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts` | PASS: 3 files, 36 tests |
| `npx tsc --noEmit --pretty false` | PASS: exit 0 |
| `E2E_BASE_URL=http://localhost:4444 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile` | PASS: 4 tests |

## Visual Evidence

Evidence directory:

`docs/work/2026-07-07_frontend-corrective-day-migration-wave-10/artifacts/rework-01/`

| File | SHA256 |
|------|--------|
| `3001-day-2026-07-05-top.png` | `6d00ad188d42794af8761410809282bb496ae011669f1f255c74a14ca11684aa` |
| `3001-day-2026-07-05-middle.png` | `f5ed103df57ced008fddab5b8938bfef078edba95958321986f9397092da2610` |
| `3001-day-2026-07-05-bottom.png` | `9a442acb7989edb39669c9464b23dc729deea3aaf90bdcc5b61e161c454b1728` |
| `main-day-2026-07-05-top.png` | `d7f5b7deb0c26f296690c0163ab7b2a7431da96b8c24a3000c9603e8390b4eb3` |
| `main-day-2026-07-05-middle.png` | `cad253e45422e470f50da59d7e99b185329e0d3503813a091501f4f75c085e22` |
| `main-day-2026-07-05-bottom.png` | `54a8f92edf4845565ca596e2bf41945e0b84ddfdcf2fb49923f07567943d6049` |
| `summary.json` | Contains route, base URLs, viewport, scroll positions, detected section order, screenshot paths, and screenshot hashes. |

The 3001 oracle was read from `http://localhost:3001`. Main evidence used `http://localhost:4444` with Playwright route interception and the same contract-valid fixtures as the mock-visual e2e. Production `3002` was not restarted.

## Notes

- `next-env.d.ts` remains a generated working-tree side effect and is not part of this rework commit.
- Existing unrelated untracked `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md` were not touched.

## Push

Push attempted: No
Push: NOT_ATTEMPTED
