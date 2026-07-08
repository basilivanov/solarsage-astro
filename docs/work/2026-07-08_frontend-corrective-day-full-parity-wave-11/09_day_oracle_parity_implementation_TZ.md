# Wave 11 Day Oracle Parity Implementation TZ

You are the coder agent. Implement the `/day/2026-07-05` parity gaps found in the accepted audit.

Read first:

- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/07_oracle_audit_rework_01_report.md`
- `docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/08_oracle_audit_rework_01_review.md`

Use current WIP as the starting point. You may modify product code and tests in this step. Commit only after the required gates pass.

## Objective

Make main/candidate `/day/2026-07-05` visually and behaviorally match the 3001 oracle frontend while still using real backend data/contracts.

Allowed:

- real data values differ from mock text,
- real chart can have a different number of planets/aspects,
- frontend display adapters can translate/aggregate backend keys into product UI labels.

Forbidden:

- runtime mocks in production code,
- static fake astrology calculations on the frontend,
- raw backend/internal labels visible to users,
- English sign/aspect/technical labels visible in `/day`,
- weakening e2e assertions,
- committing `next-env.d.ts` generated churn unless intentionally required.

## Required Product Changes

### 1. Concrete Today: 12 product-facing sphere rows

Files likely involved:

- `components/today/concrete-day-advice.tsx`
- `lib/display/sphere-labels.ts`
- tests under `__tests__/lib/display/` and `e2e/mock-visual/day.spec.ts`

Implement a real display contract for product spheres:

- Define a canonical 12-item product sphere list in the display layer:
  - `work` -> `Работа`
  - `money` -> `Деньги`
  - `documents` -> `Документы`
  - `relationships` -> `Отношения`
  - `sport` -> `Спорт`
  - `communication` -> `Общение`
  - `health` -> `Здоровье`
  - `decisions` -> `Решения`
  - `travel` -> `Поездки`
  - `creativity` -> `Творчество`
  - `study` -> `Учёба`
  - `shopping` -> `Покупки`

Map all known backend technical keys into those 12 buckets. At minimum cover:

- `work_status_achievement`
- `money_security_resources`
- `finance_money`
- `legal_affairs`
- `partnerships_contracts`
- `relationships_partnership`
- `relationships`
- `body_energy_health`
- `thinking_speech_learning`
- `communication_learning`
- `home_family_roots`
- `home_family`
- `creativity_self_expression`
- `travel_adventure`
- `long_distance`
- `education`
- `higher_education`
- `philosophy`
- `spirituality_inner_growth`
- `healing`
- `career_ambition`
- `crisis_transformation`
- `crisis_transformation_control`
- `inner_background_unconscious`
- `meaning_expansion_vector`
- `daily_routine`
- `service_routine`
- `joint_finance`
- `debts`
- `investment`
- `inheritance`
- `hidden_matters`

Rules:

- `ConcreteDayAdvice` must not fall back to raw key display.
- Unknown keys must map to a safe product bucket or a safe generic label such as `Сфера`, never `Some English Key` and never snake_case.
- Expanded state should expose 12 product rows in the canonical order.
- Compact state should show the first 6 rows.
- Header/count/filter shell should match 3001: `КОНКРЕТНО СЕГОДНЯ`, `N благоприятно`, `N осторожно`, `все 12 сфер`.
- No numeric scores in visible row text.
- Advice text may be deterministic UI microcopy derived from score/verdict/product bucket, but do not invent specific astrological calculations.

### 2. Day Summary: preserve 3001 shell with real values

File likely involved:

- `components/today/day-summary-card.tsx`

Keep dynamic real values, but match the 3001 presentation shell:

- first line inside card should include selected date and weekday, e.g. `5 ИЮЛ · ВОСКРЕСЕНЬЕ`;
- status label stays real, e.g. `Поддерживающий день`, `Ровный день`, `Напряжённый день`;
- main status line stays real from `STATUS_META`;
- compact facts should render as short rows with icon + text and muted `→` suffix when applicable;
- use available real data only:
  - lunar `phase`, `illumination`, `voidOfCourse` from calendar;
  - `topFlags` from API;
  - `planetInfluences`;
  - if you pass through existing API `periodContext` from `adaptTodayPayload`, keep it typed in `lib/contracts/today.ts` with Zod and use it only for real fields such as `yearRuler`.

Do not fabricate unsupported facts such as planetary hour if no API/contract field exists.

### 3. Day Chart: 3001 visual shell + real `dayChart`

Files likely involved:

- `components/today/day-chart.tsx`
- optionally a small display helper in `lib/display/`
- `app/globals.css` only if needed, scoped carefully

Requirements:

- Use `payload.dayChart` real data.
- Do not cap/hide planets just to match 3001 planet count.
- Match the 3001 visual shell:
  - no top card header `КАРТА ДНЯ / SOLARSAGE`;
  - date label and `КАРТА ДНЯ` remain centered inside the wheel;
  - wheel sits visually like the 3001 oracle after concrete advice;
  - static aspect-type legend below the wheel with labels:
    - `соединение`
    - `оппозиция`
    - `тригон`
    - `квадратура`
    - `секстиль`
  - no raw aspect pair list like `☉ trine ☉`.
- Preserve click/tap/keyboard interaction.
- Planet popover must match the 3001 class of presentation:
  - compact card below/inside chart area,
  - Russian planet label,
  - Russian sign label, e.g. `♋ Рак · 1 дом`,
  - Russian motion label only if needed,
  - no `Знак: Cancer`,
  - no raw English sign names.
- Use deterministic display maps for signs, planets, house themes, and aspect labels. These are display helpers, not mock data.

### 4. History Widget: 3001 `БЛИЖАЙШИЕ ДНИ` card

File likely involved:

- `components/today/astro-history-widget.tsx`

Match the 3001 history presentation:

- section heading outside the card with divider lines and uppercase `БЛИЖАЙШИЕ ДНИ`;
- one curated educational astronomy/space-history card;
- large year style;
- category label such as `миссия`;
- title and short description;
- no multiple compact list rows for `/day/2026-07-05`;
- no duplicated `1997 · миссия`;
- this is educational static content, not personal astrology and not runtime API mocking.

### 5. E2E mock visual contract

Files likely involved:

- `e2e/mock-visual/day.spec.ts`
- `e2e/mock-visual/fixtures/day-2026-07-05.ts`
- possibly `e2e/mock-visual/fixtures/calendar-2026-07.ts`

Update the mock visual e2e so it tests the same frontend on contract-valid intercepted API payloads:

- fixture must include a valid `dayChart`, not `dayChart: null`, for ready state;
- fixture must include raw technical `sphereScores` keys that prove the display adapter maps them to product labels;
- ready test must expect `day-chart`, not `day-chart-unavailable`;
- assert `ConcreteDayAdvice` contains product labels such as `Работа`, `Деньги`, `Документы`, `Отношения`, `Спорт`, `Общение`;
- expand and assert 12 rows;
- assert page does not contain:
  - `Crisis Transformation Control`
  - `Inner Background Unconscious`
  - `Cancer`
  - raw snake_case keys
  - visible score suffixes;
- assert chart legend contains the 5 Russian aspect labels;
- click the first `day-chart-planet`, assert popover appears and contains Russian sign/house format;
- assert history widget shows `БЛИЖАЙШИЕ ДНИ` and does not render the old multi-row duplicate list.

Do not weaken the missing-fixture tracker.

## Required Evidence After Implementation

Create:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/implementation-01/`

Capture:

- `candidate-00-full-scroll.png`
- `candidate-01-top.png`
- `candidate-02-concrete-today-expanded.png`
- `candidate-03-chart-before.png`
- `candidate-04-chart-after-click.png`
- `candidate-05-reading-why-week-history.png`
- `summary-implementation.json`

The summary must include:

- section order,
- concrete advice labels,
- concrete advice row count after expand,
- raw/debug strings found,
- chart legend labels,
- chart popover text after click,
- history heading and card text.

## Required Gates

Run at minimum:

```bash
npx vitest run __tests__/lib/display/sphere-labels.test.ts
E2E_BASE_URL=http://127.0.0.1:7777 npx playwright test e2e/mock-visual/day.spec.ts
```

Also run any existing relevant unit test you add or modify.

If broader `npx vitest run` is practical, run it too. If it fails on known unrelated permission/document issues, report exact failure and do not claim full green.

Before commit:

- check `git diff`;
- remove accidental generated churn in `next-env.d.ts` if it only points to `.next-prod/types/routes.d.ts`;
- do not touch unrelated untracked files such as `.grace/`, `grace.db`, `skills/`, or unrelated docs.

Commit when all required gates pass.

Commit message:

```text
fix(day): match oracle presentation with real data
```

## Report

Write:

`docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/10_day_oracle_parity_implementation_report.md`

The report must include:

- files changed,
- what product gaps were closed,
- what real-data differences intentionally remain,
- test commands and exact pass/fail summary,
- evidence artifact links,
- commit SHA if committed.

## Callback

When done, run:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 11 Day Oracle Parity Implementation ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/10_day_oracle_parity_implementation_report.md. Artifacts: docs/work/2026-07-08_frontend-corrective-day-full-parity-wave-11/artifacts/implementation-01/. Branch: main. Commit: <SHA or NO_COMMIT>."}'
```

