# Wave 14 Calendar Full Oracle Parity Implementation Report

Date: 2026-07-08
Branch: main
Mode: implementation, no push, no deploy

## Summary

Implemented the Wave 14 calendar parity work against the accepted TZ:

- backend calendar contract now emits lunar facts in `contractVersion=2`;
- frontend contract preserves expanded lunar fields and strict `phaseIndex` range;
- calendar title renders from `payload.month` in Russian, not backend English `title`;
- day tap selects locally; footer CTA is the only route-opening action;
- calendar grid renders an oracle-like compact month window over the backend payload;
- day-view lunar strip and moon mode render backend lunar facts as glyphs/labels only;
- selected-day footer is visible above the bottom tab bar in the captured tall viewport.

No production imports of `lib/mocks/calendar.ts`, MSW, `lib/demo-data.ts`, or oracle frontend moon calculations were added.

## Files Changed

Backend:

- `apps/api/app/schemas/calendar.py`
- `apps/api/app/services/calendar_service.py`
- `apps/api/app/services/lunar_facts_service.py`
- `apps/api/tests/test_calendar_endpoints.py`

Frontend/contracts:

- `lib/contracts/calendar.ts`
- `lib/lunar-presentation.ts`
- `packages/contracts/openapi.json`
- `packages/contracts/_generated.ts`
- `components/calendar/calendar-screen.tsx`
- `components/calendar/lunar-calendar-strip.tsx`

Tests/fixtures:

- `__tests__/api/calendar.test.ts`
- `__tests__/components/CalendarScreen.test.tsx`
- `__tests__/contracts/calendar.test.ts`
- `__tests__/hooks/useCalendar.test.ts`
- `e2e/calendar.spec.ts`
- `e2e/mock-visual/calendar.spec.ts`
- `e2e/mock-visual/fixtures/calendar-2026-07.ts`

Artifacts/report:

- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/artifacts/implementation/*.png`
- `docs/work/2026-07-08_frontend-corrective-calendar-full-parity-wave-14/07_calendar_parity_implementation_report.md`

## Backend Contract Changes

- `CalendarLunarFields` now supports:
  - `phase`: stable enum key;
  - `phaseIndex`: `0..7`;
  - `phaseLabel`: localized short label;
  - `illumination`;
  - `moonSign`;
  - `moonSignLabel`;
  - `lunarDay`;
  - `voidOfCourse`.
- `/api/calendar` now returns `meta.contractVersion = 2`.
- `CalendarService` calls `LunarFactsService` when building each day.
- `LunarFactsService` is backend-owned and documented as `mean-synodic-v1`; `false` for `voidOfCourse` means computed-not-void, while `null` remains reserved for unknown/uncomputed.
- Calendar status/access logic remains on the existing Wave 13 path.

## Frontend Behavior Changes

- Header month label is derived from `month` as Russian nominative month, e.g. `Июль 2026`.
- Calendar renders the compact visual month window from backend day records instead of displaying full previous/current/next month streams.
- Day cells no longer navigate directly.
- Footer CTA calls `onOpenDay` and navigates to `/day/YYYY-MM-DD`.
- Lunar strip renders phase chips, strip glyphs, illumination, and optional selected detail from backend fields.
- Moon mode renders backend phase glyphs and lunar day numbers; missing data remains a fallback only for genuinely missing backend facts.
- Frontend lunar helpers are presentation-only value-to-glyph/label mappings; no frontend date-based lunar/astrological calculations were added.

## Verification

Fresh required commands:

```bash
git status --short --branch
```

Result: exit 0. Relevant implementation files modified/untracked; unrelated `.grace/`, `grace.db`, `skills/`, and `docs/superpowers/...` remain untracked and unstaged.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.38s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts
```

Result: exit 0, 4 files passed, `45 passed`.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/mock-visual/calendar.spec.ts
```

Result: exit 0, `10 passed` across Chromium and mobile.

```bash
E2E_BASE_URL=http://localhost:3000 npx playwright test e2e/calendar.spec.ts
```

Result: exit 1 locally. Both Chromium and mobile reach a ready calendar but fail at:

```text
getByTestId('lunar-calendar-strip') expected visible; element not found
```

Reason: the only canonical API available to the dev frontend is systemd `:8000`, and this task explicitly forbids deploying or restarting systemd. The running API reports `git_sha=unknown` and returns `calendar/v1`, `contractVersion=1`, with null lunar fields. The local backend tests verify the new v2 code, but the running API has not loaded it.

Dev server note:

- `curl -I http://127.0.0.1:3000/calendar` initially failed because no dev server was running.
- Started local frontend with `pnpm exec next dev -p 3000`.
- An earlier incorrect attempt, `pnpm dev -- -p 3000`, failed because Next parsed `-p` as a project directory.
- The dev server was stopped after verification.

## Basil Real-Data Spot Check

Against the currently running real API on `:8000` with Telegram HMAC for `tg_user_id=833478509`:

- `/api/calendar?month=2026-07`, `2026-07-08`: `dayStatus=supportive`, `access.state=full`, `reason=active_referral_days`, `referralDaysLeft=4`.
- `/api/day/2026-07-08`: `dayStatus=supportive`, same access fields.
- `/api/calendar?month=2026-07`, `2026-07-12`: `dayStatus=steady`, `access.state=locked`, `reason=outside_access_window`.
- `/api/day/2026-07-12`: `dayStatus=steady`, same locked access fields, `detail=null`.
- The same running API returned `contractVersion=1` and null lunar fields, confirming the real e2e limitation above.

## Screenshot Artifacts

Captured from local frontend `http://localhost:3000` with the mock-visual v2 fixture:

- `artifacts/implementation/3002-mobile-calendar-top.png`
- `artifacts/implementation/3002-mobile-calendar-lunar.png`
- `artifacts/implementation/3002-tall-calendar-top.png`
- `artifacts/implementation/3002-tall-calendar-lunar.png`
- `artifacts/implementation/3002-desktop-calendar-top.png`
- `artifacts/implementation/3002-desktop-calendar-lunar.png`

## Residual Gaps

- Real e2e cannot pass in this no-deploy/no-systemd-restart session because production/systemd API `:8000` still serves the old v1 calendar contract.
- Lunar facts currently use the documented backend approximation. Replacing it with SolarSage/Swiss-Ephemeris longitudes should be a future backend-only service change that preserves the v2 frontend contract.
