# TZ: Wave 14 Calendar Full Oracle Parity Implementation

Date: 2026-07-08
Status: ready for coder
Owner: architect
Branch: `main`
Mode: implementation

## 1. Goal

Implement `/calendar` so current main/3002 matches the 3001 mock-preview oracle visually and behaviorally while remaining backed by real backend data and contracts.

Use the accepted audit as source of truth:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/05_rework_01_review.md`
- screenshots in `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/audit/`

## 2. Non-Negotiable Constraints

- Do not import runtime mocks, MSW, `lib/mocks/calendar.ts`, demo data, or oracle client astrology into production code.
- Do not calculate astrological/lunar facts in frontend code.
- Preserve Telegram HMAC/session auth and real API flow.
- Preserve backend-owned access states and day scoring.
- Do not restart systemd, push, or deploy.
- Do not stage unrelated files: `.grace/`, `grace.db`, `skills/`, `docs/superpowers/`.
- Keep edits tightly scoped to calendar/backend contract/test files required by this wave.

## 3. Architecture Decisions

### Backend-Owned Lunar Facts

Add backend-owned lunar facts through a shared service/helper. Do not bury reusable lunar logic directly in the React layer or as ad hoc frontend helpers.

Recommended implementation shape:

- create a shared backend helper/service, for example `apps/api/app/services/lunar_facts_service.py`;
- call it from `CalendarService` when building calendar days;
- make it reusable by `/day` later if needed;
- use SolarSage/Sun-Moon longitudes or a documented backend-side algorithm;
- document `null` vs `false` semantics.

Contract shape to support:

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

If you choose a smaller first implementation, it must still support oracle parity for visible July 2026 calendar states and must not fake missing facts in the frontend.

### Frontend Presentation

Port presentation and interactions from the 3001 oracle:

- Russian month title, e.g. `Июль 2026`;
- compact oracle-like current-month calendar composition;
- rich day-view lunar card/strip above grid;
- phase glyphs and lunar day numbers in `Луна` mode;
- selected-day footer visible above bottom nav;
- day tap selects locally;
- footer CTA is the only route-opening action;
- preserve bottom nav and stable mobile shell.

## 4. Files To Inspect

Read before editing:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/04_rework_01_report.md`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/05_rework_01_review.md`
- `apps/api/app/schemas/calendar.py`
- `apps/api/app/services/calendar_service.py`
- `apps/api/tests/test_calendar_endpoints.py`
- `lib/contracts/calendar.ts`
- `lib/api/calendar.ts`
- `lib/calendar.ts`
- `lib/date.ts`
- `components/calendar/calendar-screen.tsx`
- `components/calendar/lunar-calendar-strip.tsx`
- `components/calendar/mood-icon.tsx`
- `__tests__/components/CalendarScreen.test.tsx`
- `__tests__/contracts/calendar.test.ts`
- `__tests__/api/calendar.test.ts`
- `__tests__/hooks/useCalendar.test.ts`
- `e2e/calendar.spec.ts`
- `e2e/mock-visual/calendar.spec.ts`
- `e2e/mock-visual/fixtures/calendar-2026-07.ts`

Oracle references:

- `/opt/solarsage-astro-mock-preview/components/calendar/calendar-screen.tsx`
- `/opt/solarsage-astro-mock-preview/components/calendar/lunar-calendar-strip.tsx`
- `/opt/solarsage-astro-mock-preview/components/calendar/mood-icon.tsx`
- `/opt/solarsage-astro-mock-preview/lib/calendar.ts`
- `/opt/solarsage-astro-mock-preview/lib/moon.ts`

Use oracle moon code only to understand expected output. Do not port it to production frontend.

## 5. Required Implementation Tasks

### Task A — Backend Contract And Lunar Facts

- Extend `CalendarLunarFields` with `phase_index`, `phase_label`, and `moon_sign_label` using camelCase aliases through existing schema conventions.
- Define stable phase keys and labels.
- Populate lunar fields in `/api/calendar` for calendar days through backend-owned service/helper.
- Preserve existing access/status fields.
- Add backend tests proving lunar fields are populated and have valid ranges.
- Preserve calendar/day scoring consistency from Wave 13.

### Task B — Frontend Contract/Adapter

- Update Zod/calendar types for the expanded lunar contract.
- Keep `steady -> even` adapter behavior unless backend contract changes intentionally.
- Add tests for parsing expanded lunar fields and missing/null semantics.
- Ensure visible title uses Russian month formatting, not English `payload.title`.

### Task C — Calendar UI Parity

- Rework `components/calendar/calendar-screen.tsx` against oracle screenshots.
- Day tap must select only.
- Footer CTA must call `onOpenDay`.
- Selected-day footer must be visible above bottom nav in mobile/tall layouts.
- Render compact current-month composition matching oracle, while not corrupting backend access/status data.
- Preserve stable test selectors and accessibility states.

### Task D — Lunar UI Parity

- Rework `components/calendar/lunar-calendar-strip.tsx` to render oracle-like day-view lunar card/strip from real backend fields.
- In `Луна` mode, render phase glyphs and lunar day numbers from backend fields.
- Render current-day marker and selected-state treatment like oracle.
- Fallback state remains only for genuinely missing backend lunar facts, not normal July 2026 data.

### Task E — Tests And Visual Evidence

- Update unit/contract/API tests.
- Update mock visual calendar fixture with real-shaped expanded lunar fields.
- Update Playwright calendar tests for:
  - localized month title;
  - local day selection;
  - footer CTA navigation;
  - lunar card/strip visible;
  - lunar mode phase glyphs/day numbers;
  - no horizontal overflow mobile;
  - missing fixture tracking if mock-visual route interception is used.
- Capture updated 3002 screenshots comparable to accepted artifacts.

## 6. Required Verification

Run and report exact results:

```bash
git status --short --branch
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/calendar.spec.ts
```

If local `3000` is unavailable, start a dev server without touching `3002` and report the command/URL. Do not restart production systemd services.

Also run a real-data spot check for Basil without mutating the real user:

- `tg_user_id=833478509`, username `basil_ivanov`;
- compare `/api/calendar?month=2026-07` and `/day/2026-07-08`;
- include a Sunday/access check for `2026-07-12`.

## 7. Output Report

Write:

```text
docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/07_calendar_parity_implementation_report.md
```

Include:

- files changed;
- backend contract changes;
- frontend behavior changes;
- tests run with exact results;
- screenshot artifact paths;
- known residual gaps, if any.

## 8. Commit Rules

Commit only relevant implementation, tests, fixtures, and report files.

Do not stage unrelated:

- `.grace/`
- `grace.db`
- `skills/`
- `docs/superpowers/`

Do not push or deploy.

## 9. Callback

When complete, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave 14 Calendar Full Parity Implementation ready for architect review. Report: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/07_calendar_parity_implementation_report.md. TZ: docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/06_calendar_parity_implementation_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```
