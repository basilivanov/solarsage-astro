# Wave 11 Day Oracle Parity Rework 01 TZ

You are the coder agent. Rework the implementation from commit `4cf0e16` according to the architect review:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/11_day_oracle_parity_implementation_review.md`

Do not rewrite history. Make a follow-up commit on `main` after gates pass.

## Objective

Close the remaining architectural/visual gaps while preserving the improvements already made:

- keep real backend data,
- keep the interactive day chart,
- keep 12 product-facing concrete advice rows,
- keep raw/debug strings out of the UI,
- keep e2e route interception tests.

## Required Fixes

### 1. Fix DaySummaryCard to match the 3001 compact shell

File:

- `components/today/day-summary-card.tsx`

Required visual structure:

```text
[card]
  top row:
    left:  5 ИЮЛ · ВОСКРЕСЕНЬЕ
    right: <emoji> <real status label>
  second row:
    real status line
  divider
  compact fact rows
[/card]
```

Remove the current large standalone emoji block and title stack.

Allowed real-data differences:

- status label/line is real from `dayStatus`;
- lunar phase/illumination is real from calendar;
- top flag/top planet text is real from API.

Do not fabricate unsupported astrology facts on the frontend. In particular:

- do not derive a "weekday ruler" from `date.getDay()` unless there is a real API/contract field for it;
- do not add a "planetary hour" or similar calculated fact in frontend code.

If only three real fact rows are available, render three rows. The shell must match 3001; the data values do not need to be identical to 3001.

### 2. Make product sphere mapping key-based and canonical

File:

- `lib/display/sphere-labels.ts`

Define an explicit product sphere bucket contract, for example:

```ts
export type ProductSphereKey =
  | "work"
  | "money"
  | "documents"
  | "relationships"
  | "sport"
  | "communication"
  | "health"
  | "decisions"
  | "travel"
  | "creativity"
  | "study"
  | "shopping"
```

Provide:

- canonical product sphere list/order;
- backend key -> product key map;
- product key -> label/icon map;
- safe helper for unknown keys.

Every known backend key from the previous TZ must map into one of the 12 product keys. `home_family_roots` and `home_family` must not map to `Семья` for the `/day` concrete advice contract because `Семья` is not one of the 12 oracle rows.

Use a conservative mapping for family/home keys, for example into `relationships`, unless you document a better product bucket.

Unknown user-facing fallback must be safe Russian text such as `Сфера` or `Другая сфера`, never title-cased English and never snake_case.

Update `__tests__/lib/display/sphere-labels.test.ts`:

- remove the expectation that unknown key becomes `Some Unknown Key`;
- assert unknown key is safe Russian generic text;
- assert every `SPHERE_PRODUCT_MAP`/backend mapping resolves to one of the 12 canonical product labels/keys;
- assert `home_family_roots`, `home_family`, `crisis_transformation_control`, `inner_background_unconscious`, and `meaning_expansion_vector` resolve into canonical product buckets.

### 3. Fix ConcreteDayAdvice to avoid fabricated scored rows

File:

- `components/today/concrete-day-advice.tsx`

Required behavior:

- Build exactly 12 rows in canonical product order.
- Aggregate real backend `sphereScores` into product buckets by product key, not label string comparison.
- If multiple real scores map to one bucket, choose deterministically. Preferred simple rule:
  - choose the score with strongest non-neutral signal: caution first (`<=3`), then good (`>=6`), then best rank;
  - document the rule in code briefly.
- If a bucket has no real score, render:
  - `verdict: "unavailable"`,
  - no fake `score: 5.0`,
  - safe text such as `Нет отдельного сигнала на эту сферу.`,
  - muted/unavailable dot.
- Header counts must count only real scored good/caution rows, not unavailable filler rows.
- No visible numeric scores.
- No raw/debug labels.

Keep 12 rows after expand.

### 4. Fix DayChart semantic labels

File:

- `components/today/day-chart.tsx`

Use the Russian sign formatter in `aria-label` too. A planet in Cancer should be announced as `Солнце в Рак, 1 дом` or better `Солнце в Раке, 1 дом` if you add prepositional sign labels.

Visible popover should remain Russian and compact.

### 5. Fix implementation evidence

File likely involved:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/capture-implementation.cjs`

Regenerate:

- `artifacts/implementation-01/candidate-01-top.png`
- `artifacts/implementation-01/candidate-02-concrete-today-expanded.png`
- `artifacts/implementation-01/candidate-03-chart-before.png`
- `artifacts/implementation-01/candidate-04-chart-after-click.png`
- `artifacts/implementation-01/candidate-05-reading-why-week-history.png`
- `artifacts/implementation-01/candidate-00-full-scroll.png`
- `artifacts/implementation-01/summary-implementation.json`

Make sure `candidate-05-reading-why-week-history.png` actually shows the bottom/history area, not the top viewport.

The summary must include:

- day summary structure facts;
- concrete advice labels;
- real/unavailable row counts;
- raw/debug strings found;
- chart aria/sample popover text;
- history heading/card text.

### 6. Tests

Run at minimum:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
npx vitest run __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
```

Update e2e assertions as needed so they catch:

- no `Some Unknown Key`;
- no `Семья` in concrete advice if it is not part of canonical 12;
- no raw English sign text in visible page text;
- day summary compact shell text is present.

Do not weaken missing-fixture tracking.

## Report

Write:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/13_day_oracle_parity_rework_01_report.md`

Include:

- fixes made;
- tests run with exact pass/fail summary;
- evidence links;
- implementation commit SHA;
- HEAD/report commit SHA if different.

## Commit

Commit after gates pass.

Suggested commit message:

```text
fix(day): close oracle parity review gaps
```

## Callback

When done, run:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Day Oracle Parity Rework 01 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/13_day_oracle_parity_rework_01_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/implementation-01/. Branch: main. Commit: <SHA>."}'
```

