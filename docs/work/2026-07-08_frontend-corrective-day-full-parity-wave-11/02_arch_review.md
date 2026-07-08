# Architect Review: Wave 11 — `/day` Full Oracle Parity

Date: 2026-07-08
Branch: `main`
Reviewed commit: `85667e7`
Status: REJECTED

## Summary

Wave 11 is not acceptable. The commit fixes a small part of the summary card and hides `TodayImportantAccordion`, but it does not deliver the required 3001 oracle parity.

The main blockers are structural:

- the active `/day` advice component was not fixed;
- the day chart is still static and non-interactive;
- the bottom history widget was regressed from curated astronomy history into three date-specific astrology snippets;
- required visual/interaction evidence was not produced;
- e2e tests were weakened instead of extended.

## Findings

### P1 — `/day` still renders the old `ConcreteDayAdvice`, so visible scores and long technical labels remain

Files:

- `components/today/today-screen.tsx:43`
- `components/today/today-screen.tsx:186`
- `components/today/concrete-day-advice.tsx:117-128`
- `components/today/concrete-day-advice.tsx:219-228`

The commit rewrites `components/today/today-practical-list.tsx`, but `/day` does not use that component. The real route still imports and renders `ConcreteDayAdvice`.

That active component still:

- derives labels through `getSphereLabel`, so real backend keys can remain long product-unfriendly labels;
- appends `row.score.toFixed(1)` into visible UI;
- keeps the same wider row structure that caused the visible mismatch.

This directly violates Wave 11 requirements:

- no visible score numbers in `Конкретно сегодня`;
- no raw/technical/domain labels;
- short product labels like `Работа`, `Деньги`, `Документы`, `Отношения`, `Спорт`, `Общение`;
- 3001-style compact advice table.

Required fix: apply the product-category mapping and no-score rendering to the active component (`ConcreteDayAdvice`), or replace the screen usage with a corrected component and remove dead/unused code.

### P1 — Day chart remains static; required interactions were not implemented

File: `components/today/day-chart.tsx:52-247`

The chart component is unchanged from the static renderer:

- no `"use client"`;
- no selected planet state;
- no clickable/tappable planet targets;
- no `role="button"`;
- no `tabIndex`;
- no Enter/Space keyboard handling;
- no `data-testid="day-chart-planet"`;
- no `data-testid="day-chart-planet-popover"`;
- no selected visual emphasis;
- no popover;
- the static raw planet list still renders below the chart at `components/today/day-chart.tsx:235-242`.

This fails the explicit Wave 11 acceptance criteria that 3002 must be behaviorally equivalent to 3001: clicking/tapping a planet opens a detail popover and selected state is visible.

Required fix: port the 3001 interaction model over real `payload.dayChart`, using real planet positions/aspects and productized Russian labels.

### P1 — Astro history widget was regressed into date-specific astrology snippets and disappears for most dates

File: `components/today/astro-history-widget.tsx:7-16`

The previous curated astronomy/history widget was replaced by only three hard-coded dates:

```ts
2026-07-05, 2026-07-06, 2026-07-07
```

The copy is also astrology-style day content:

```text
Солнце в Раке — время заботы о доме и семье
```

That is not the 3001 bottom history block. The requirement was a curated educational astronomy/space-history widget equivalent to the oracle (`В этот день` / `Ближайшие дни`, e.g. `1997 · миссия · «Марс Пасфайндер» на Марсе`) and a deterministic nearest-event fallback so normal dates do not silently lose the block.

Required fix: restore/port the curated educational event model, including exact/nearby behavior, and keep it rendered after `WeekStrip` and before the disclaimer.

### P1 — Required Wave 11 visual/interaction evidence is missing

Files:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/01_agent_report.md`
- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/`

The report lists no artifact paths and no hashes. The expected artifact folder does not exist:

```text
docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/final/
```

Required evidence from the TZ was:

- top/middle/bottom screenshots for 3001 and 3002;
- chart before/after click for 3001 and 3002;
- `summary.json` with section order, chart interactive counts, popover text, and hidden/present section checks.

Without this evidence the wave cannot be accepted, especially because the largest requirement is visual/behavioral parity.

### P1 — E2E was weakened and does not test required parity

File: `e2e/mock-visual/day.spec.ts:196-204`

The spec now expects `practical-list` in `sectionOrder`, but the page renders `concrete-day-advice`. The test also removes the previous `astro-history-widget` assertion by replacing it with comments.

Missing required e2e assertions:

- no `today-important-accordion`;
- `astro-history-widget` visible near the bottom;
- real chart fixture with `dayChart` exists;
- `day-chart-planet` targets exist;
- clicking a chart planet opens `day-chart-planet-popover`;
- no static raw list like `Sun · 1 дом`;
- no raw labels such as `Crisis Transformation Control`;
- no visible numeric scores in `Конкретно сегодня`.

Required fix: make the e2e spec stricter, not weaker, and add/adjust fixtures so the chart interaction path is exercised.

### P2 — `next-env.d.ts` is dirty after build

File: `next-env.d.ts`

The working tree currently has:

```diff
-import "./.next/types/routes.d.ts";
+import "./.next-prod/types/routes.d.ts";
```

This generated side effect must be restored before the next report/callback unless there is a separate documented architecture decision.

### P2 — Report overclaims gate coverage

File: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/01_agent_report.md`

The report says build succeeded and targeted tests passed, but omits:

- exact `pnpm build` command output;
- required Playwright command result;
- required artifacts;
- whether 3002 was restarted;
- known intentional differences.

Independent architect checks:

```bash
npx vitest run __tests__/components/TodayScreen.test.tsx __tests__/guardrails/no-runtime-mocks.test.ts --reporter=dot
```

Result: PASS, 15 tests.

```bash
npx tsc --noEmit --pretty false
```

Result: PASS.

These passing checks do not cover the rejected Wave 11 requirements.

## Decision

Rejected. Implement `03_rework_01_TZ.md`.
