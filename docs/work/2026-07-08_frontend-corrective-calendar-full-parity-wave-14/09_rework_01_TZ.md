# TZ: Wave 14 Calendar Parity Rework 01

Date: 2026-07-08
Status: ready for coder
Branch: `main`
Base commit reviewed: `2bd66f6`
Architect review: `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/08_calendar_parity_implementation_review.md`

## Goal

Fix the blocking review findings from Wave 14 so `/calendar` can be accepted as a real-data, oracle-parity migration.

This is not a broad redesign. Keep the current backend-owned contract direction and existing local-selection/footer-CTA behavior, but make the implementation verifiable and visually faithful to 3001.

## Required Work

### 1. Make typecheck green

Run:

```bash
pnpm exec tsc --noEmit --pretty false
```

Fix all errors.

Known current errors:

- `__tests__/components/TodayScreen.test.tsx:303`
- `__tests__/components/TodayScreen.test.tsx:386`

Use the new lunar contract correctly:

- `phase`: stable enum key, e.g. `full_moon`, `waning_gibbous`;
- `phaseLabel`: Russian display label, e.g. `Полнолуние`, `Убывающая Луна`.

Do not loosen `CalendarLunarFields.phase` to arbitrary `string` unless you document and justify a real compatibility reason.

### 2. Align mock-visual scenario with oracle date

The accepted oracle screenshots for Wave 14 show July 8, 2026 as current/selected.

Update mock-visual fixtures/tests/artifacts so the comparable 3002 evidence also uses July 8, 2026:

- `e2e/mock-visual/fixtures/calendar-2026-07.ts`
- `e2e/mock-visual/calendar.spec.ts`
- screenshot capture artifacts under `artifacts/implementation/`

Expected:

- fixture `generatedAt` around `2026-07-08`;
- July 8 has `isToday: true`;
- tests freeze clock to `2026-07-08T12:00:00Z` where determinism is needed;
- selected footer in screenshots says `Сегодня` / `8 июля 2026`;
- lunar mode selected day is July 8.

If you believe July 5 should be the reference scenario, stop and provide fresh 3001+3002 oracle screenshots for July 5. Otherwise use July 8.

### 3. Make fixture lunar facts match backend/oracle facts

The current fixture table is not aligned with the backend/oracle algorithm. Replace it.

Use `apps/api/app/services/lunar_facts_service.py` as the accepted backend source for v2 facts in this wave.

Sentinel expected values from current backend service:

```text
2026-07-05: phase=waning_gibbous, phaseIndex=5, phaseLabel=убыв. Луна, illumination=70, lunarDay=21
2026-07-08: phase=waning_crescent, phaseIndex=7, phaseLabel=убыв. серп, illumination=39, lunarDay=24
2026-07-11: phase=waning_crescent, phaseIndex=7, phaseLabel=убыв. серп, illumination=12, lunarDay=27
2026-07-23: phase=waxing_gibbous, phaseIndex=3, phaseLabel=раст. Луна, illumination=64, lunarDay=9
```

Add tests/assertions that catch future fixture drift for at least those sentinel dates.

Do not import backend Python directly into frontend tests. Either hardcode a generated table with source comments or implement a test-only JS helper that mirrors the documented backend algorithm.

### 4. Port oracle SVG phase glyph presentation

Replace emoji phase rendering with an oracle-style SVG glyph.

Source to inspect:

```text
/opt/solarsage-astro-mock-preview/components/calendar/lunar-calendar-strip.tsx
```

Port only the presentation component/styles:

- custom SVG `PhaseGlyph`;
- dark/gold phase colors;
- small glyph sizing used by strip/legend;
- selected/ring treatment where applicable.

Do not port:

- `computeMoonPhaseForDay`;
- `getLunarDay`;
- `getVoidOfCourse`;
- any frontend date-based lunar calculation.

All glyphs must be driven by backend `phaseIndex`.

Update places that currently render emoji:

- `lib/lunar-presentation.ts` if it remains;
- `components/calendar/lunar-calendar-strip.tsx`;
- `components/calendar/calendar-screen.tsx` moon-mode cells and selected footer if visually needed.

### 5. Recapture visual evidence

After fixes, capture new 3002 screenshots:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-mobile-calendar-top.png
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-mobile-calendar-lunar.png
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-tall-calendar-top.png
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-tall-calendar-lunar.png
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-desktop-calendar-top.png
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/3002-desktop-calendar-lunar.png
```

The tall screenshots must be directly comparable with:

```text
artifacts/audit/3001-tall-calendar-top.png
artifacts/audit/3001-tall-calendar-lunar.png
```

## Verification Required

Run and report exact results:

```bash
git status --short --branch
git diff --check HEAD~1..HEAD
pnpm exec tsc --noEmit --pretty false
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts __tests__/components/TodayScreen.test.tsx __tests__/app/day-page.test.tsx
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

If real e2e still fails only because systemd API `:8000` is not restarted and still serves `contractVersion=1`, report that explicitly. Do not restart systemd in this rework unless instructed.

Also run:

```bash
rg -n "lib/mocks/calendar|mocks/calendar|lib/demo-data|USE_FIXTURES|msw|mockServiceWorker|computeMoonPhaseForDay|getLunarDay|getVoidOfCourse" app components lib apps/api e2e __tests__ packages --glob '!node_modules/**'
```

The only allowed hits for mock/demo/oracle moon calculations are test-only files, docs, or the oracle path comments. Product code must not import them.

## Report

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/10_rework_01_report.md
```

Include:

- files changed;
- how each review finding was resolved;
- exact verification command results;
- screenshot artifact paths;
- remaining real-runtime/deploy gaps, if any.

## Commit

Commit only relevant files. Do not stage unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/`

## Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Parity Rework 01 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/10_rework_01_report.md. Review: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/08_calendar_parity_implementation_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/09_rework_01_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```

