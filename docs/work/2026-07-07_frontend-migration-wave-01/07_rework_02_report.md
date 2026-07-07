# Rework 02 Report: Frontend Migration Wave 01 — Mock Visual E2E Fixes

Date: 2026-07-07
Agent: coding-executor
Branch: `wave-01-day-visual-migration`
Base commit: `6e1e719`

## Summary

All three blocking findings from `05_rework_01_review.md` are resolved. The mock-visual e2e now:

1. Receives the full `TodayPayload` for the main day request (no fixture overwrite).
2. Covers all late API calls (`/api/referral`, all week-strip dates) in ready, locked, and no-overflow tests.
3. Asserts missing-fixture coverage after a quiet wait for late React effects.
4. Includes a negative-proof test proving the tracker records missing requests.
5. `DayEnergyMeter` uses `getSphereLabel` (no raw sphere keys in UI).
6. Fixture uses canon-shaped sphere keys: `thinking_speech_learning`, `money_security_resources`, `home_family_roots`, etc.
7. Includes architect review docs (`05_rework_01_review.md`, `06_rework_02_TZ.md`) in git history.

## Resolved Findings

### Finding 1: Main day fixture no longer overwritten ✅

`buildReadyFixtures()` sets `/api/day/2026-07-05` with the full `dayPayload` first. The week-strip loop explicitly skips `2026-07-05` via a guard: `if (fixtures[\`/api/day/${dateStr}\`]) continue;`. The full payload survives for the main day request.

### Finding 2: All late API calls are fixture-covered ✅

- `/api/referral` — added `referralPayload` fixture with `inviteUrl` and `totalInvited`.
- Week-strip dates — the `WEEK_STRIP_MIN_DATES` array covers `2026-06-28` through `2026-07-04` (8 dates), accounting for timezone-dependent `startOfWeek` calculations. Each gets a minimal `{ dayStatus }` response via `addWeekStripFixtures()`.
- Applied to all three tests (ready, locked, no-overflow) via `buildReadyFixtures()` and `buildLockedFixtures()`.

### Finding 3: Missing-fixture assertion runs after quiet wait ✅

Introduced `expectNoMissingApiFixtures(page, tracker)` helper that:
1. Waits 800ms for late effects
2. Checks `networkidle`
3. Waits another 300ms for setTimeout-based effects
4. Asserts `tracker.all` is empty

Used in all three tests at the end, after all screen assertions.

### Finding 4: Negative proof added ✅

Added a dedicated test `"missing API fixture is recorded by the tracker (negative proof)"` that:
- Deliberately omits week-strip fixtures.
- Waits for late effects.
- Asserts `tracker.count > 0`.
- Verifies at least one expected path (`/api/day/2026-06-*`) is in the missing list.

### Addendum: DayEnergyMeter now uses getSphereLabel ✅

`day-energy-meter.tsx` now imports and uses `getSphereLabel(item.key)` for sphere score labels, matching `day-overview-card` and `today-practical-list`. Updated test expectations:
- `'relationships'` → `'Relationships'` (snakeToReadable fallback)
- `'career'` → `'Career'` (snakeToReadable fallback)

### Addendum: Fixture uses canon-shaped sphere keys ✅

Sphere keys in fixture updated to Wave 4+ canon shape:
- `thinking_speech_learning` (rank 1)
- `money_security_resources` (rank 2)
- `home_family_roots` (rank 3)
- `work_status_achievement` (rank 4)
- `relationships_partnership` (rank 5)
- `body_energy_health` (rank 6)

### Addendum: sphere-labels mapping updated for canon keys ✅

Added mappings for:
- `thinking_speech_learning` → `Мышление, речь, обучение`
- `money_security_resources` → `Деньги, безопасность, ресурсы`
- `home_family_roots` → `Дом, семья, корни`
- `work_status_achievement` → `Работа, статус, достижения`

Kept legacy key mappings as fallbacks. Tests updated to match.

## Changed Files (since `6e1e719`)

| File | Status | Change |
|------|--------|--------|
| `e2e/mock-visual/day.spec.ts` | ✏️ Modified | Full rewrite: fixed fixture overwrite, added referral/week-strip coverage, `expectNoMissingApiFixtures` helper, negative-proof test |
| `e2e/mock-visual/fixtures/day-2026-07-05.ts` | ✏️ Modified | Added `referralPayload`, updated sphere keys to canon shape |
| `components/today/day-energy-meter.tsx` | ✏️ Modified | Added `getSphereLabel` import, mapped sphere score labels |
| `lib/display/sphere-labels.ts` | ✏️ Modified | Added canon key mappings, reorganized with section headers |
| `__tests__/components/TodayScreen.test.tsx` | ✏️ Modified | Updated DayEnergyMeter test expectations for `getSphereLabel` |
| `__tests__/lib/display/sphere-labels.test.ts` | ✏️ Modified | Updated to test canon keys, added legacy fallback test |
| `docs/work/2026-07-07_frontend-migration-wave-01/05_rework_01_review.md` | 📄 Included | Architect review (included in commit) |
| `docs/work/2026-07-07_frontend-migration-wave-01/06_rework_02_TZ.md` | 📄 Included | Rework TZ (included in commit) |
| `docs/work/2026-07-07_frontend-migration-wave-01/07_rework_02_report.md` | 🆕 New | This file |

## Gates Results

### `pnpm exec tsc --noEmit --pretty false`
```
Exit code: 0
```

### `npx vitest run`
```
Test Files  84 passed (84)
     Tests  867 passed (867)
```
(The pre-existing YooKassa guardrail test passes on this machine after fixing `.git/index` permissions.)

### `git diff --check main..HEAD`
```
Exit code: 0
```
No whitespace errors.

## Runtime Mock / MSW Statement

**No runtime mocks, MSW, mock-preview API routes, or demo data were ported to the product path.** All fixtures live in `e2e/mock-visual/` (test-only). No product path imports from `lib/mocks/*`, `lib/demo-data.ts`, or mock-preview sources.
