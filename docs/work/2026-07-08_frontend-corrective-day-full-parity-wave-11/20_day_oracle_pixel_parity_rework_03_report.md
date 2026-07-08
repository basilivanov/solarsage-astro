# Day Oracle Pixel Parity Rework 03 Report

**Date**: 2026-07-08
**Branch**: `main`
**Rework 03 Commit SHA**: `ab145535359a16f8ef94a73748232e0c25a29879` (follow-up fix)
**Hygiene/Whitespace Commit SHA**: `f1ec4a92184e1559a879d5a9546c65f4eeee7e17` (HEAD)

---

## 1. Changed Files

*   **`components/today/today-screen.tsx`**:
    *   Updated to pass `dayStatus` and `planetInfluences` as props into `ConcreteDayAdvice` to provide full real day context.
*   **`components/today/concrete-day-advice.tsx`**:
    *   Removed `unavailable` from concrete advice verdicts. All 12 rows are always rendered in one of `good | caution | avoid | neutral` states.
    *   No row text contains placeholder/unavailable phrases like `Нет отдельного сигнала на эту сферу.` or `Данные появятся после расчёта.`.
    *   Implemented a multi-tier view-model adapter (`buildConcreteAdviceRows`):
        1.  Checks mapped `sphereScores` (chooses the strongest signal if multiple map to the same bucket).
        2.  Checks `topFlags` aspect verdicts (scans aspect title for associated planets).
        3.  Checks `planetInfluences` scores (good `>= 6.0` or caution `<= 3.0` for associated planets).
        4.  Falls back to `dayStatus` (`supportive` -> `good`, `tense` -> `caution`, `steady` -> `neutral`).
    *   Derived header counts directly from displayed row verdicts: `good` counts as `благоприятно`, `caution`/`avoid` counts as `осторожно`. A supportive day with sparse scores will now display `> 0 благоприятно` (4 in our visual mock fixture).
*   **`__tests__/components/TodayScreen.test.tsx`**:
    *   Added a unit test for `buildConcreteAdviceRows` validating that 12 rows are returned with no `unavailable` status, supportive context yields `> 0` good rows, and counts are derived correctly.
*   **`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-rework-03.cjs`**:
    *   Reworked the capture script to use scoped selectors for both oracle and candidate and case-insensitive text locator waits.
    *   Correctly counts placeholders and `unavailable` statuses and returns the exact 12 row objects for visual summary checks.
*   **Whitespace Cleaning**:
    *   Cleaned trailing whitespace and trailing EOF empty lines in all modified/staged files.

---

## 2. Rework 03 Evidence List

All screenshots are captured under `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/`:
*   **`oracle-concrete-collapsed.png`** / **`candidate-concrete-collapsed.png`**
*   **`oracle-concrete-expanded.png`** / **`candidate-concrete-expanded.png`**
*   **`oracle-chart-after-click.png`** / **`candidate-chart-after-click.png`**
*   **`summary.json`**: Confirms 12 row objects mapped correctly, `placeholderTextCount: 0`, `unavailableStatusCount: 0`, and no tap highlight focus outline.

---

## 3. Verification Commands & Results

*   **Vitest**:
    *   `npx vitest run __tests__/lib/display/sphere-labels.test.ts` (8 passed)
    *   `npx vitest run __tests__/components/TodayScreen.test.tsx` (15 passed)
*   **Playwright E2E**:
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts` (8 passed)
*   **Hygiene Check**:
    *   `git diff --check HEAD~2..HEAD` (clean, no trailing whitespace or new EOF lines)
