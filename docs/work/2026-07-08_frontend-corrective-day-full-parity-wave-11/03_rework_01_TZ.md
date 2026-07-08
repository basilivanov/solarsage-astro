# Rework 01 TZ: Wave 11 — Fix Actual `/day` Parity Gaps

Date: 2026-07-08
Branch: `main`
Role: coding executor in `tmux astro:0.0`
Base rejected commit: `85667e7`
Architect review: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/02_arch_review.md`

## Goal

Fix the real Wave 11 blockers. The previous commit changed some files, but did not make the active `/day` UI match 3001.

Do not claim completion until the actual rendered `/day/2026-07-05` on the candidate build satisfies the required visual and interaction checks.

## Required Fixes

### 1. Fix the active `Конкретно сегодня` component

The active `/day` screen renders:

```ts
components/today/today-screen.tsx -> ConcreteDayAdvice
```

Fix `components/today/concrete-day-advice.tsx` or replace that screen usage with a corrected component.

Requirements:

- No visible numeric scores (`row.score.toFixed(1)` must not render).
- Product category labels must be short and oracle-like:
  - `Работа`
  - `Деньги`
  - `Документы`
  - `Отношения`
  - `Спорт`
  - `Общение`
  - plus deterministic labels for remaining real backend spheres.
- No raw/technical/domain labels such as:
  - `Crisis Transformation Control`
  - `Inner Background Unconscious`
  - unknown snake_case split into English title words.
- Preserve the 3001-style section shape:
  - heading with side lines;
  - good/caution counts;
  - `все 12 сфер` expand/collapse;
  - compact row list;
  - no horizontal overflow.
- If `components/today/today-practical-list.tsx` remains unused after this, either remove the dead code changes or clearly justify why the file remains.

### 2. Implement real-data interactive `DayChart`

Fix `components/today/day-chart.tsx`.

Requirements:

- Keep real `chart: DayChartData | null` input.
- Do not calculate fake chart positions from mock natal constants.
- Use real `chart.houses`, `chart.transitPlanets`, and `chart.aspects`.
- Port 3001 interaction model:
  - `"use client"`;
  - selected planet state;
  - clickable/tappable planet glyphs;
  - larger transparent hit area;
  - selected planet visual emphasis;
  - detail popover below chart;
  - aspect legend under chart;
  - no static raw planet list under chart.
- Add accessibility:
  - each planet target has `role="button"`;
  - `tabIndex={0}`;
  - Enter/Space toggles selection;
  - `aria-label` names the planet in Russian.
- Add stable test IDs:
  - `data-testid="day-chart"`;
  - `data-testid="day-chart-planet"`;
  - `data-testid="day-chart-planet-popover"`.
- Popover text:
  - Russian planet label;
  - Russian sign label if `planet.sign` exists;
  - `{N} дом` if `planet.house` exists;
  - motion/retrograde state if available;
  - short deterministic product description based on planet + house.
- Do not show visible raw English labels like `Sun · 1 дом` outside the popover.

### 3. Restore/port the educational history widget

Fix `components/today/astro-history-widget.tsx`.

Requirements:

- Restore a curated astronomy/space-history event model equivalent to the 3001 widget.
- For `/day/2026-07-05`, render the Mars Pathfinder event near July 4:
  - heading can be `Ближайшие дни`;
  - year `1997`;
  - category `миссия`;
  - title `«Марс Пасфайндер» на Марсе`.
- Exact date event heading: `В этот день`.
- Nearby event heading: `Ближайшие дни`.
- Include deterministic nearest-event fallback within the same month, so normal dates do not silently omit the widget.
- Do not use astrology snippets as history-widget content.
- Keep `data-testid="astro-history-widget"`.
- Render after `WeekStrip` and before `today-bottom-disclaimer`.

### 4. Strengthen tests instead of weakening them

Update tests to assert the real requirements.

Required component/unit checks:

- `__tests__/components/TodayScreen.test.tsx`
  - no `today-important-accordion` on accessible `/day`;
  - `astro-history-widget` present for `/day/2026-07-05`;
  - `today-bottom-disclaimer` comes after `astro-history-widget`;
  - `concrete-day-advice` visible text does not include score strings such as `5.5`;
  - `concrete-day-advice` visible text uses short product labels.
- Add a focused test for `DayChart` interaction:
  - render real chart props;
  - `getAllByTestId("day-chart-planet")` count > 0;
  - click first planet;
  - `day-chart-planet-popover` appears with Russian label and house.

Required Playwright checks:

- `e2e/mock-visual/day.spec.ts`
  - section order includes `concrete-day-advice`, `day-chart` or `day-chart-unavailable`, `week-strip`, `astro-history-widget`, `today-bottom-disclaimer`;
  - no `today-important-accordion`;
  - bottom internal scroll shows `astro-history-widget`;
  - no raw labels such as `Crisis Transformation Control`;
  - no visible score numbers in concrete advice;
  - when fixture includes `dayChart`, chart planet targets exist and clicking opens popover;
  - no static raw planet list under the chart (`Sun · 1 дом` must not appear as default visible list).

If current mock fixture has `dayChart: null`, add a contract-valid `dayChart` fixture for the interaction test.

### 5. Produce required evidence

Create:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/rework-01/
```

Capture:

- `3001-day-2026-07-05-top.png`
- `3001-day-2026-07-05-middle.png`
- `3001-day-2026-07-05-bottom.png`
- `3002-day-2026-07-05-top.png` or `main-day-2026-07-05-top.png` if using a preview port
- `3002-day-2026-07-05-middle.png` or `main-day-2026-07-05-middle.png`
- `3002-day-2026-07-05-bottom.png` or `main-day-2026-07-05-bottom.png`
- `3001-day-chart-before.png`
- `3001-day-chart-after-click.png`
- `3002-day-chart-before.png` or `main-day-chart-before.png`
- `3002-day-chart-after-click.png` or `main-day-chart-after-click.png`
- `summary.json`

`summary.json` must include:

- base URL used for oracle and candidate;
- section order for candidate;
- `todayImportantExists`;
- `historyExists`;
- chart interactive planet count for oracle and candidate;
- chart popover text after click for oracle and candidate;
- screenshot SHA256 hashes;
- intentional text differences caused by real backend data.

### 6. Clean generated files and docs

- Restore `next-env.d.ts` to:

```ts
import "./.next/types/routes.d.ts";
```

- Do not touch unrelated untracked files:
  - `.grace/`
  - `grace.db`
  - `skills/`
  - `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`
- Include the Wave 11 work docs in the final commit if they are not already tracked:
  - `00_TZ.md`
  - `02_arch_review.md`
  - `03_rework_01_TZ.md`
  - updated `01_agent_report.md`

## Verification Commands

Run at minimum:

```bash
npx vitest run __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts
npx tsc --noEmit --pretty false
pnpm build
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day.spec.ts --project=mobile
```

If using a preview port instead of live 3002 for e2e/evidence, state the exact port in the report and still verify live 3002 status if possible.

## Report

Update:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/01_agent_report.md
```

Include:

- new commit hash;
- files changed;
- exact tests run and results;
- artifact paths and hashes;
- whether 3002 was restarted;
- known intentional differences from 3001 due to real backend data;
- confirmation that `next-env.d.ts` is clean.

## Commit And Callback

Commit only intentional files on `main`.

After commit, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Rework 01 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/01_agent_report.md. Review: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/02_arch_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/03_rework_01_TZ.md. Branch: main. Commit: <commit_hash>."}'
```
