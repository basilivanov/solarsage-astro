# Wave 11 Rework 03 TZ — Concrete Advice Product Contract and Evidence Fix

Owner: coder agent
Branch: `main`
Scope: follow-up fix after Rework 02
Report path: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/20_day_oracle_pixel_parity_rework_03_report.md`
Artifacts path: `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/`

## Read First

Read the review before coding:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/18_day_oracle_pixel_parity_rework_02_review.md`

Do not repeat broad Wave 11 work. This is a narrow follow-up.

## Mission

Fix the remaining concrete advice and evidence gaps so `/day/[date]` matches the 3001 product presentation contract while still using real adapted payload data.

Keep the Rework 02 chart visual port unless a small fix is required for tests/evidence. Do not touch unrelated day sections.

## Binding Requirements

### 1. Concrete Advice Rows

Every canonical product sphere must render as a product row, never as an unavailable placeholder.

Required:

- Remove `unavailable` from concrete advice row verdicts.
- `data-status` must only be one of:
  - `good`
  - `caution`
  - `avoid`
  - `neutral`
- No row text may contain:
  - `Нет отдельного сигнала`
  - `Данные появятся`
  - `ожидается`
- Missing/sparse real data must fall back to oracle neutral/product copy, not placeholder copy.
- Keep the exact 12 emoji icons and oracle row order:
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

### 2. Real Data Adapter

Use real adapted payload fields. Do not import runtime mocks/static API fixtures.

Required:

- `ConcreteDayAdvice` must receive and use:
  - `dayStatus`
  - `planetInfluences`
  - `topFlags`
  - `notes`
  - `sphereScores`
- Update `components/today/today-screen.tsx` to pass `dayStatus` and `planetInfluences`.
- The view-model should merge real signals in a deterministic order:
  1. mapped `sphereScores`;
  2. relevant `planetInfluences` / `topFlags`;
  3. `dayStatus`;
  4. oracle neutral fallback.
- A supportive day with sparse scores must not display `0 благоприятно` unless all available real signals are explicitly negative/caution. For the current mock visual supportive fixture, concrete advice must show `> 0 благоприятно`.
- Counts must be derived from displayed row verdicts:
  - `good` => `благоприятно`;
  - `caution` and `avoid` => `осторожно`;
  - `neutral` => not counted.

Implementation guidance:

- Keep the 3001 oracle copy tables/rules as product copy.
- It is acceptable to export a pure helper such as `buildConcreteAdviceRows` for tests.
- Do not add local date astrology calculations or 3001 mock API imports.

### 3. Tests

Strengthen tests so this cannot regress again.

Required E2E assertions in `e2e/mock-visual/day.spec.ts`:

- collapsed row count is 6;
- expanded row count is 12;
- collapse returns to 6;
- exact emoji order is present;
- no row has `data-status="unavailable"`;
- page does not contain `Нет отдельного сигнала` or `Данные появятся`;
- for the supportive mock visual fixture, parsed `благоприятно` count is greater than 0;
- chart popover still opens;
- chart target still has no default visible outline/tap highlight after click.

Add a unit test if you export the view-model helper:

- sparse data returns 12 rows;
- no `unavailable`;
- supportive context yields at least one `good` row;
- counts computed from displayed verdicts.

### 4. Evidence Capture

Create fresh artifacts under:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/`

Required files:

- `oracle-concrete-collapsed.png`
- `oracle-concrete-expanded.png`
- `candidate-concrete-collapsed.png`
- `candidate-concrete-expanded.png`
- `candidate-chart-after-click.png`
- `summary.json`

Fix `capture-rework-02.cjs` or create `capture-rework-03.cjs`.

`summary.json` must be correct and scoped. It must include:

- `oracle.rows` and `candidate.rows`: exactly 12 row objects each with `{ icon, label, text, status }`;
- `candidate.placeholderTextCount`;
- `candidate.unavailableStatusCount`;
- `candidate.goodCount`;
- `candidate.cautionCount`;
- `candidate.toggleTextBefore`;
- `candidate.toggleTextAfter`;
- `candidate.collapsedRowCount`;
- `candidate.expandedRowCount`;
- `candidate.hasFocusOutline`;
- `candidate.webkitTapHighlightColor`.

Do not use brittle selectors such as `section button` or emoji `text.length === 2`.
Add `data-testid` / `data-*` attributes where useful; this is allowed by our UI Semantic/Test Contract.

### 5. Verification Commands

Run and report exact results:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
npx vitest run __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
git diff --check HEAD~2..HEAD
```

If you add a new unit test file, include that command too.

## Commit and Callback

Commit the Rework 03 implementation and report on `main`.

Do not include unrelated untracked paths:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`

After commit, call back:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Day Oracle Pixel Parity Rework 03 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/20_day_oracle_pixel_parity_rework_03_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/pixel-rework-03/. Branch: main. Commit: <SHA>."}'
```
