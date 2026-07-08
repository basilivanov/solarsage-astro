# TZ: Wave 14 Calendar Oracle Audit Rework 01

Date: 2026-07-08
Status: ready for coder
Owner: architect
Branch: `main`
Mode: audit/report rework only

## 1. Goal

Rework the calendar audit report so it is detailed enough to become the implementation source of truth for a later 1:1 calendar parity migration.

Do not edit product source code. This rework is documentation and optional audit artifacts only.

## 2. Read First

Read:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/00_TZ.md`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/01_oracle_audit_report.md`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/02_arch_review.md`
- all screenshots in `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/audit/`

Use the existing 12 screenshots as evidence. Capture extra screenshots only if needed to answer a missing interaction/state.

## 3. Required Fixes

Address every finding in `02_arch_review.md`.

At minimum, the new report must include:

- complete visual matrix covering header, locale, prev/next controls, segmented control, day-view lunar card, week labels, day grid, selected/today state, out-of-month days, locked days, summary footer, bottom nav, and lunar mode;
- complete interaction matrix covering day tap, CTA tap, month navigation, `Дни`/`Луна` switch, locked day tap, and selected summary behavior;
- complete data/contract matrix with exact JSON paths, types, nullability, backend source of truth, frontend adapter impact, cache/versioning notes, and tests;
- direct answers to all 13 questions from `00_TZ.md` section 9;
- explicit statement that month title localization differs (`Июль 2026` vs `July 2026`) and must be fixed;
- explicit statement that selected-day summary footer is missing/not visible on 3002 in the captured top/tall artifacts;
- reclassification of `lib/mocks/calendar.ts` as test-only unless proven otherwise;
- no recommendation to delete `components/grace/*` or mocks unless the report includes proof and explains why deletion is required for calendar parity;
- exact evidence for calendar/day scoring consistency and Basil access checks, or mark those as not fully verified.

## 4. Architecture Direction To Use In The Report

For lunar fields, do not recommend frontend astrology calculations.

Preferred architecture:

- create or use a shared backend lunar calculation/helper/service;
- have `/api/calendar` populate `CalendarLunarFields`;
- have `/api/day` use the same source if day UI needs lunar facts;
- keep frontend responsible only for presentation and localization;
- represent phase as stable semantic data, not just a UI emoji.

Recommended contract shape to evaluate in the report:

```json
{
  "lunar": {
    "phase": "waning_crescent",
    "phaseIndex": 7,
    "phaseLabel": "убыв. серп",
    "illumination": 39.0,
    "moonSign": "Cancer",
    "moonSignLabel": "Рак",
    "lunarDay": 24,
    "voidOfCourse": false
  }
}
```

If you choose a different contract shape, explain why.

## 5. Output

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md
```

Do not overwrite `01_oracle_audit_report.md`.

Allowed to commit:

- `04_rework_01_report.md`
- optional new files under `artifacts/audit-rework-01/`

Do not stage or commit:

- product source edits;
- `.grace/`;
- `grace.db`;
- `skills/`;
- `docs/superpowers/`;
- temporary Playwright specs.

## 6. Verification

Before reporting complete:

```bash
git status --short --branch
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts
```

If you capture additional screenshots, include the exact Playwright command and result.

## 7. Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Oracle Audit Rework 01 ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md. Review: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/02_arch_review.md. Rework TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/03_rework_01_TZ.md. Branch: main. Commit: <COMMIT_SHA_OR_NO_COMMIT>. Push: NOT_ATTEMPTED"}'
```

Return only a short completion line in tmux after callback.
