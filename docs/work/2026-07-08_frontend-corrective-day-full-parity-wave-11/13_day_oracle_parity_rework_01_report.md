# Day Oracle Parity Rework Report: Wave 11

**Date**: 2026-07-08  
**Branch**: `main`  
**Initial Implementation Commit**: `1d3f290b21b069d3d3ef0c79e602b9e6a0c9a29e` (or `1d3f290`)  
**Follow-up Rework Commit**: `99cbcce6d8a3be05e3f169542a2253018260b13d` (or `99cbcce`)  

---

## 1. Fixes Made

*   **DaySummaryCard**: 
    *   Reworked to place the date header (`5 ИЮЛ · ВОСКРЕСЕНЬЕ`) and day status (`🌊 Ровный день` or `✨ Поддерживающий день`) inside the compact card header.
    *   Removed the large standalone emoji block and title stack.
    *   Removed the fabricated weekday ruler and planetary hour. Only renders the fact rows that have real backend/calendar data.
*   **lib/display/sphere-labels.ts**:
    *   Defined the explicit `ProductSphereKey` type representing the 12 canonical product spheres.
    *   Mapped all 32 known backend technical keys directly to one of the 12 product keys. Specifically, `home_family_roots` and `home_family` now map to `relationships` (`Отношения`) to avoid rendering a non-canonical `Семья` row.
    *   Changed the fallback for unknown keys to return a safe Russian generic text (`Другая сфера`) instead of title-cased English.
    *   Updated unit tests to assert key mapping correctness and verify no English fallback occurs.
*   **ConcreteDayAdvice**:
    *   Aggregated `sphereScores` into the 12 canonical product buckets by key.
    *   Implemented a deterministic aggregation rule: if multiple scores map to a single bucket, choose the strongest non-neutral signal (caution first, then good, then best rank).
    *   If a product bucket has no real backend scores, it renders `verdict: "unavailable"` and advice text `"Нет отдельного сигнала на эту сферу."` without fabricating any fake score.
    *   Adjusted counts (`N благоприятно`, `N осторожно`) to only sum real scored rows.
*   **DayChart**:
    *   Updated `aria-label` formatting on planet nodes to fully translate sign names to Russian prepositional form (e.g. `Солнце в Раке, 1 дом` instead of `Солнце в Cancer, 1 дом`).
*   **Evidence Capture**:
    *   Fixed `scrollToText` in `capture-implementation.cjs` to use Playwright locator `waitFor` so that it reliably waits for elements to render before scrolling.
    *   Replaced page reload with a simple deselection click on the planet node.
    *   `candidate-05-reading-why-week-history.png` now correctly captures the bottom reading and space history card.
    *   Full scroll screenshot (`candidate-00-full-scroll.png`) now correctly shows all 12 spheres expanded.

---

## 2. Verification Results

All tests have been run and verified as passing:
*   **Vitest**:
    *   `__tests__/lib/display/sphere-labels.test.ts`: 8 passed.
    *   `__tests__/components/TodayScreen.test.tsx`: 14 passed.
*   **Playwright E2E**:
    *   `e2e/mock-visual/day.spec.ts`: All 8 tests passed successfully on Chromium and Mobile viewports.

---

## 3. Evidence Artifacts

Generated artifacts under `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/implementation-01/`:
- `candidate-00-full-scroll.png`: stitched full page layout showing all 12 spheres expanded.
- `candidate-01-top.png`: top viewport showing the correct compact card header.
- `candidate-02-concrete-today-expanded.png`: concrete advice section with 12 spheres.
- `candidate-03-chart-before.png`: day chart before click.
- `candidate-04-chart-after-click.png`: day chart with popover.
- `candidate-05-reading-why-week-history.png`: bottom section.
- `summary-implementation.json`: parsed metadata.
