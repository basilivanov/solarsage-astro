# Day Oracle Pixel Parity Report: Wave 11 Rework 02

**Date**: 2026-07-08  
**Branch**: `main`  
**Commit SHA**: `cc2af5a2eb2cb90b271d49e6f3dfa2799fdbe89` (or `cc2af5a`)

---

## 1. Changed Files

*   **`components/today/concrete-day-advice.tsx`**:
    *   Ported the exact 3001 visual and interaction logic.
    *   Uses 12 product sphere emojis in the canonical order.
    *   Row layout uses the identical classes, padding, emoji size, label width (`w-[68px]`), text size, dot sizes, and expanded row backgrounds.
    *   Collapses to exactly 6 rows by default, showing `все 12 сфер` in the header and `Показать ещё 6 сфер ▾` in the footer.
    *   Expands to 12 rows, changing the header action text to `свернуть` and hiding the footer. Toggles back to 6 rows on a second click.
    *   Derives advice counts based on displayed verdicts: `good` counts as `благоприятно`, `caution`/`avoid` counts as `осторожно`.
    *   Renders a safe gray placeholder dot and text (`Нет отдельного сигнала на эту сферу.`) for unscored spheres instead of fabricating scores or using candidate-only labels.
*   **`components/today/day-chart.tsx`**:
    *   Ported the exact visual shell and geometry from the 3001 oracle chart (SVG size, radii, radial backgrounds, zodiac ring slices, house spokes, and center labels).
    *   Uses real backend data inputs (`chart.transitPlanets`, `chart.houses`, `chart.aspects`) while applying the exact 3001 presentation styles.
    *   Added `SIGN_PREPOSITIONAL` mapping to fully translate planet node `aria-label`s into prepositional Russian (e.g. `Солнце в Раке, 1 дом`), preventing any English sign/house text leaks.
    *   Fixed the Telegram WebView focus outline bug: applied `outline: "none"` and `WebkitTapHighlightColor: "transparent"` inline styles to the planet target nodes to completely eliminate the default blue focus rectangle.
*   **`e2e/mock-visual/day.spec.ts`**:
    *   Strengthened test assertions to verify the collapsed row count (6), expanded row count (12), double toggling back to 6, exact canonical emoji order, translated `aria-label` format, Russian popover, and the absence of a focus outline.
*   **`e2e/mock-visual/route-interception.ts`**:
    *   Gracefully intercepts telemetry/log requests to `/api/_log` to prevent test failures on mobile viewports due to background warning posts.

---

## 2. Rework 02 Evidence List

All screenshots are captured under `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-02/`:
*   **`oracle-concrete-collapsed.png`** / **`candidate-concrete-collapsed.png`**
*   **`oracle-concrete-expanded.png`** / **`candidate-concrete-expanded.png`**
*   **`oracle-chart-before.png`** / **`candidate-chart-before.png`**
*   **`oracle-chart-after-click.png`** / **`candidate-chart-after-click.png`**
*   **`summary.json`**: Verified parity on row counts, emojis, legend labels, and no focus outline (`candidate.hasFocusOutline: false`).

---

## 3. Test Command Results

*   **Vitest**:
    *   `npx vitest run __tests__/lib/display/sphere-labels.test.ts` (8 passed)
    *   `npx vitest run __tests__/components/TodayScreen.test.tsx` (14 passed)
*   **Playwright E2E**:
    *   `E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts` (8 passed)
