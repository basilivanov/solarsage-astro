# Wave 14 Calendar Parity Implementation Review

Date: 2026-07-08
Reviewed commit: `2bd66f6`
Decision: REWORK REQUIRED

## Summary

The implementation moved the calendar in the right direction architecturally: backend-owned lunar fields exist, contracts were extended, local selection vs footer CTA is present, and the targeted backend/unit calendar tests pass.

It is not acceptable yet for main/product parity. There are blocking issues:

- TypeScript typecheck is red.
- The mock-visual fixture and screenshots are not comparable to the 3001 oracle because they use 2026-07-05 while the oracle evidence uses 2026-07-08.
- The fixture contains lunar values that do not match the backend/oracle calculation.
- Lunar glyphs are rendered as emoji, while the 3001 oracle uses custom SVG phase glyphs; this is visibly different and violates the current "icons/style 1:1" requirement.

## Verification Run

```bash
git diff --check HEAD~1..HEAD
```

Result: exit 0.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_calendar_endpoints.py -q
```

Result: exit 0, `12 passed in 1.60s`.

```bash
npx vitest run __tests__/components/CalendarScreen.test.tsx __tests__/hooks/useCalendar.test.ts __tests__/contracts/calendar.test.ts __tests__/api/calendar.test.ts
```

Result: exit 0, 4 files passed, `45 passed`.

```bash
pnpm exec tsc --noEmit --pretty false
```

Result: exit 2.

Errors:

```text
__tests__/components/TodayScreen.test.tsx(303,11): error TS2322: Type '"Полнолуние"' is not assignable to type ...
__tests__/components/TodayScreen.test.tsx(386,7): error TS2322: Type '"Убывающая Луна"' is not assignable to type ...
```

## Findings

### P0 — `main` is not typecheck-clean after the calendar contract change

Evidence:

- `pnpm exec tsc --noEmit --pretty false` fails.
- `__tests__/components/TodayScreen.test.tsx:303` and `:386` still pass display labels into `CalendarLunarFields.phase`.
- The new generated contract makes `phase` a stable enum key, with the display string belonging in `phaseLabel`.

Required fix:

- Migrate existing Today/day test fixtures and any impacted call sites to the new semantic contract:
  - `phase`: stable key, e.g. `full_moon` or `waning_gibbous`;
  - `phaseLabel`: Russian display label, e.g. `Полнолуние` or `Убывающая Луна`.
- Run full typecheck successfully.
- Do not loosen the contract back to arbitrary `string` unless there is a reviewed API compatibility reason.

### P1 — Calendar visual evidence is not apples-to-apples with oracle 3001

Evidence:

- Oracle artifact `artifacts/audit/3001-tall-calendar-top.png` shows selected/current `8 июля 2026`.
- Implementation artifact `artifacts/implementation/3002-tall-calendar-top.png` shows selected/current `5 июля 2026`.
- `e2e/mock-visual/calendar.spec.ts:87` and `:115` freeze browser time to `2026-07-05T12:00:00Z`.
- `e2e/mock-visual/fixtures/calendar-2026-07.ts:154` and `:167` mark July 5 as generated/current day.

Required fix:

- For Wave 14 parity evidence, use the same scenario as the oracle: `2026-07-08`.
- Update mock-visual fixture `isToday`, generatedAt, access window labels, and tests to use July 8 unless a fresh 3001 oracle capture is produced for July 5.
- Recapture implementation screenshots after the fix.

### P1 — Mock-visual lunar values diverge from backend/oracle lunar calculation

Evidence:

- Fixture says July 5 is `illumination: 63`, `lunarDay: 20` at `e2e/mock-visual/fixtures/calendar-2026-07.ts:62`.
- Backend `LunarFactsService` for 2026-07-05 returns illumination `70`, lunar day `21`.
- Oracle screenshot `3001-tall-calendar-top.png` also shows July 5 as `70%`.
- Fixture says July 11 is `phaseIndex: 0`, `illumination: 4` at line `68`, while backend/oracle algorithm returns waning crescent around `12%`.

Required fix:

- Fixture values must be produced from the same accepted backend/oracle algorithm, not hand-edited mismatches.
- Either:
  - hardcode a table generated from `LunarFactsService` for July 2026 and include a note/source in the fixture; or
  - implement a test-only fixture generator that mirrors the backend algorithm.
- Add an assertion that a few sentinel days match backend facts: July 5, July 8, July 11, July 23.

### P1 — Lunar glyphs are emoji, not oracle SVG glyphs

Evidence:

- `lib/lunar-presentation.ts:36` maps phase indexes to emoji strings.
- `components/calendar/lunar-calendar-strip.tsx:78`, `:110`, `:123`, and legend lines `:146-148` render those emoji.
- 3001 oracle `components/calendar/lunar-calendar-strip.tsx` uses a custom `PhaseGlyph` SVG presentation with dark/gold fills, not platform emoji.
- The current 3002 screenshots visibly differ from oracle in icon shape, color, and rendering.

Required fix:

- Port only the oracle `PhaseGlyph` presentation component/style, driven by backend `phaseIndex`.
- Do not port frontend moon calculation from 3001.
- Replace emoji glyphs in:
  - day-view lunar strip chips;
  - strip day cells;
  - lunar selected detail;
  - moon-mode calendar cells if needed for parity;
  - legend.
- Keep backend facts as the source of truth.

### P2 — Real e2e still cannot prove v2 until running API is deployed/restarted

Evidence:

- Agent report says real e2e failed because systemd API `:8000` still served `contractVersion=1` and null lunar fields.

Required fix:

- For this rework, keep the no-deploy constraint unless explicitly told otherwise.
- Report this as a residual deploy/runtime verification gap.
- After acceptance, deployment/restart must be a separate step before saying production/3002 is verified on real data.

## Acceptance Gate For Rework

The rework is acceptable only if:

- `pnpm exec tsc --noEmit --pretty false` passes.
- Backend calendar endpoint tests pass.
- Targeted calendar Vitest suite passes.
- Mock-visual calendar e2e passes.
- New screenshots show 3002 using the same July 8 scenario as 3001.
- Lunar glyphs are SVG/oracle-style, not emoji.
- Fixture lunar facts match backend/oracle facts for sentinel days.
- No production import of mocks/demo/MSW/oracle frontend moon calculations is introduced.

