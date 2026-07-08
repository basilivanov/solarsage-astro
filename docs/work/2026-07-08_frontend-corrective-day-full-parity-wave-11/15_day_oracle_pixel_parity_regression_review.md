# Wave 11 Day Oracle Pixel Parity Regression Review

Status: **REWORK REQUIRED**

Previous acceptance:

- `14_day_oracle_parity_rework_01_review.md`
- Accepted head at that time: `8af76b1`

Current decision: the previous acceptance was too weak. It validated functional/structural parity, but the user evidence from Telegram and direct comparison with the 3001 oracle shows that `/day` is still not presentation-identical to the mock-preview.

## Root Cause

The implementation approximated the 3001 presentation instead of porting the actual 3001 presentation components/tokens.

Confirmed code differences:

- Oracle concrete advice: `/opt/solarsage-astro-mock-preview/components/today/concrete-day-advice.tsx`
  - Uses emoji icons per product sphere.
  - Uses oracle copy/verdict generation and `VERDICT_META`.
  - Compact state shows 6 rows; expanded state shows 12 rows.
  - Header toggle text is `все 12 сфер` / `свернуть`; collapsed footer is `Показать ещё 6 сфер ▾`.
- Main concrete advice: `/opt/solarsage-astro/components/today/concrete-day-advice.tsx`
  - Uses `lucide-react` icons through `getIcon()`, not oracle emoji icons.
  - Uses different advice copy.
  - Counts only real scored rows, causing visible drift such as `0 благоприятно / 4 осторожно` where the oracle visual rules show a different balance for the same oracle scenario.
  - Renders unavailable rows such as `Данные появятся после расчёта`, which is not the intended oracle presentation for the day view.
- Oracle chart: `/opt/solarsage-astro-mock-preview/components/today/day-chart.tsx`
  - Has a richer SVG wheel, radial gradients, ring slices, planet colors, center gradients, motion-selected planets, and 3001 legend/popover styling.
- Main chart: `/opt/solarsage-astro/components/today/day-chart.tsx`
  - Is a simplified chart shell.
  - Uses focusable transparent SVG hit circles with `role="button"` and `tabIndex={0}`. In Telegram WebView this leaves a visible blue focus rectangle after tap.

## Findings

### P0 — Concrete advice is not the 3001 visual oracle

The visible UI still differs materially from 3001:

- icons are outline lucide icons instead of the oracle emoji set;
- row text is not oracle text;
- row backgrounds/dots do not match oracle verdict styling;
- header counts do not match the oracle presentation contract;
- collapsed/expanded behavior is not covered strongly enough by tests.

This blocks acceptance because the product requirement is exact visual transfer from 3001 with real data behind it.

### P0 — Day chart is not the 3001 visual oracle

The current chart is visually different from the 3001 chart and leaves a blue focus rectangle after tapping a planet in Telegram. The chart must port the 3001 presentation geometry/style and preserve real-data inputs.

This blocks acceptance because the user explicitly sees the mismatch in Telegram.

### P1 — Tests allowed approximation

Existing tests assert that the page is structurally usable, but they do not lock the oracle-critical visual semantics:

- exact 12 emoji icons in order;
- collapsed row count and expanded row count;
- toggle works both ways;
- exact oracle labels for the concrete section;
- chart planet tap does not produce a rectangular focus artifact;
- aspect legend labels and selected planet popover remain visible.

This allowed a non-oracle implementation to pass.

## Acceptance Direction

The next rework must port the 3001 presentation code for the affected `/day` sections and then adapt real backend data into that presentation contract. Do not continue local approximations.

The required implementation details are in:

- `16_day_oracle_pixel_parity_rework_02_TZ.md`

