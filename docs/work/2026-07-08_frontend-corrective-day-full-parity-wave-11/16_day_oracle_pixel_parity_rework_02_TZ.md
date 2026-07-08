# Wave 11 Rework 02 TZ — Day Oracle Pixel Parity

Owner: coder agent  
Branch: `main`  
Scope: `/day/[date]` concrete advice + day chart only  
Report path: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/17_day_oracle_pixel_parity_rework_02_report.md`  
Artifacts path: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-02/`

## Mission

Make `/day/[date]` in main visually and interactively match the 3001 mock-preview oracle for the concrete advice section and the interactive day chart, while keeping main connected to real backend/adapted data.

Do **not** approximate by writing a similar component. Port the actual presentation contract from the oracle files, then adapt real data into it.

Oracle files:

- `/opt/solarsage-astro-mock-preview/components/today/concrete-day-advice.tsx`
- `/opt/solarsage-astro-mock-preview/components/today/day-chart.tsx`
- relevant styles from `/opt/solarsage-astro-mock-preview/app/globals.css` if needed

Main files likely involved:

- `/opt/solarsage-astro/components/today/concrete-day-advice.tsx`
- `/opt/solarsage-astro/components/today/day-chart.tsx`
- `/opt/solarsage-astro/lib/display/sphere-labels.ts`
- `/opt/solarsage-astro/__tests__/components/TodayScreen.test.tsx`
- `/opt/solarsage-astro/e2e/mock-visual/day.spec.ts`

## Non-Negotiable Constraints

1. Production/main must not import runtime mocks or static API fixtures.
2. UI presentation may use deterministic product copy/templates from 3001. That copy is part of the UI contract, not a runtime mock API.
3. Real backend payload remains the source for date, day status, sphere score inputs, chart planets, houses, aspects, subscription/check-in state, notes, and reading content.
4. If backend data is missing for a chart, render the existing graceful unavailable state; do not fabricate planets/houses/aspects.
5. If backend sphere data is sparse, concrete advice still renders the canonical 12 product rows using the oracle presentation/copy contract. Missing real score should map to a neutral/oracle fallback display row, not to `Данные появятся после расчёта` on the main day surface.
6. Do not change unrelated tabs or pages in this rework.

## Required Work

### 1. Concrete Advice: Port 3001 Presentation

Port the visual and interaction behavior from the oracle component.

Required details:

- Section title: `КОНКРЕТНО СЕГОДНЯ`, with the same divider layout and zap icon treatment as 3001.
- Canonical row order and icons must match 3001 exactly:
  - `💼 Работа`
  - `💰 Деньги`
  - `📝 Документы`
  - `💖 Отношения`
  - `🏃 Спорт`
  - `💬 Общение`
  - `🌿 Здоровье`
  - `🎯 Решения`
  - `✈️ Поездки`
  - `🎨 Творчество`
  - `📚 Учёба`
  - `🛍️ Покупки`
- Do not render lucide icons in these rows.
- Row label column, emoji size, text size, row padding, rounded card, border, divider, dot size/color, and expanded row background tint must match 3001.
- Compact default state:
  - starts collapsed;
  - shows first 6 rows;
  - header action text is `все 12 сфер`;
  - footer action text is `Показать ещё 6 сфер ▾`.
- Expanded state:
  - shows all 12 rows;
  - header action text is `свернуть`;
  - footer action is hidden;
  - second click collapses back to 6 rows.
- Counts must follow the oracle display verdicts shown in the concrete advice rows:
  - `good` rows count as `благоприятно`;
  - `caution` and `avoid` rows count as `осторожно`;
  - `neutral` rows do not count.

Implementation guidance:

- Prefer creating a small view-model adapter such as `buildConcreteAdviceRows(...)` that takes real `sphereScores` plus available adapted day context and outputs the 3001 `Advice[]` shape: `{ sphere, icon, verdict, text }`.
- Reuse the 3001 `VERDICT_META` values unless theme tokens force a tiny adaptation.
- Use `PRODUCT_SPHERE_META.icon` if you keep the metadata centralized; remove or bypass the current lucide `iconName` rendering for this section.
- Do not rely on display label string matching. Keep the existing backend-key-to-product-key mapping.
- If you need stable deterministic copy, port the oracle copy tables/rules. That is acceptable because this is product copy, not mocked backend data.

### 2. Day Chart: Port 3001 Presentation

Port the visual structure and interaction behavior from the oracle `day-chart.tsx`, while feeding it from the real `DayChartData` contract.

Required details:

- Match 3001 chart geometry as closely as possible:
  - SVG size/radii;
  - outer radial background;
  - zodiac ring slices;
  - house rings/spokes/numbers;
  - center disk and center label;
  - planet disks, symbol colors, selected planet animation/state;
  - aspect line colors/opacities;
  - aspect legend labels and layout;
  - selected planet detail card layout.
- Keep real inputs:
  - `chart.transitPlanets`;
  - `chart.houses`;
  - `chart.aspects`;
  - `dateLabel`;
  - `dayStatus`.
- Fix Telegram tap artifact:
  - tapping a planet must not leave a visible blue rectangular focus outline around the hit target or selected planet;
  - prefer pointer-safe focus styling such as `:focus:not(:focus-visible) { outline: none; }`;
  - preserve keyboard accessibility where possible with `focus-visible` styling that is intentional and not a browser-default blue rectangle.
- Planet click/tap behavior:
  - first tap selects and opens detail card;
  - second tap on the same planet deselects or matches 3001 behavior if different;
  - tapping another planet updates the detail card.

### 3. Evidence Capture

Before and after the implementation, capture enough evidence to prove parity.

Required artifacts under `artifacts/pixel-rework-02/`:

- `oracle-concrete-collapsed.png`
- `oracle-concrete-expanded.png`
- `candidate-concrete-collapsed.png`
- `candidate-concrete-expanded.png`
- `oracle-chart-before.png`
- `oracle-chart-after-click.png`
- `candidate-chart-before.png`
- `candidate-chart-after-click.png`
- `summary.json`

`summary.json` must include:

- concrete advice icon list for oracle and candidate;
- visible row count in collapsed and expanded states;
- header count texts for oracle and candidate;
- toggle text before/after click;
- aspect legend labels for oracle and candidate;
- selected chart popover title for oracle and candidate;
- whether candidate has any visible/default focus outline after planet tap.

Use local browser screenshots. If 3001 and candidate run on different ports, state the exact ports in the report. 3001 is the oracle, 3002/main or a local dev server is the candidate.

### 4. Tests

Strengthen tests so this regression cannot pass again.

At minimum:

- Unit/component test for concrete advice view-model or component:
  - returns/render 12 canonical rows in oracle order;
  - uses the exact emoji icons;
  - collapsed shows 6 rows;
  - expand shows 12 rows;
  - collapse returns to 6 rows;
  - counts derive from displayed verdicts.
- Playwright test in `e2e/mock-visual/day.spec.ts` or a focused test:
  - asserts concrete advice default collapsed state;
  - clicks `все 12 сфер` and verifies 12 visible rows;
  - clicks `свернуть` and verifies 6 visible rows;
  - asserts the emoji icons in order;
  - clicks a chart planet, verifies the popover, and verifies no default blue rectangular focus artifact is visible/encoded in computed styles.

Run these commands and include exact results in the report:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
npx vitest run __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
```

If the local candidate server uses another port, state it. Do not claim green without command output.

### 5. Report and Commit

Write the report to:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/17_day_oracle_pixel_parity_rework_02_report.md`

Report must include:

- changed files;
- exact oracle files/sections ported;
- how real data flows into the ported presentation;
- test command results;
- artifact list;
- remaining known gaps, if any.

Commit the implementation and report on `main`.

After commit, call back:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Day Oracle Pixel Parity Rework 02 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/17_day_oracle_pixel_parity_rework_02_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-02/. Branch: main. Commit: <SHA>."}'
```

