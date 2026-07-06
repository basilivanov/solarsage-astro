# Task 6 Report: Add Check-In Real Contract And UI

## Status

DONE

## Summary

Implemented a real check-in vertical slice:

- Backend DB model and Alembic migration now support numeric mood, numeric accuracy, energy, tags, note, filled_at, updated_at, and streak fields.
- Legacy `mood` and `notes` rows remain readable through response mapping and migration backfill.
- FastAPI now exposes `POST /api/checkin`, `GET /api/checkin/{target_date}`, `GET /api/checkin/yesterday`, `GET /api/checkin/metrics`, and timezone-aware reminder date behavior.
- Frontend now has a real typed `lib/api/checkin.ts` client, check-in UI, check-in page, pure selector components, yesterday echo UI, and real profile check-in statistics.
- Contract artifacts were regenerated from Pydantic schemas.

## TDD Evidence

### Backend RED

Command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py -q
```

Initial result before implementation:

```text
6 failed, 1 passed
```

Failures showed the expected missing behavior:

- `POST /api/checkin` returned 422 for camelCase numeric payload.
- `GET /api/checkin/{target_date}` returned old snake_case/string shape.
- `/api/checkin/yesterday` was caught by the dynamic date route and returned 422.
- `/api/checkin/metrics` did not support the real aggregate contract.
- Legacy string `mood` rows returned strings instead of readable numeric response values.

### Backend GREEN

Command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py -q
```

Result:

```text
7 passed in 0.67s
```

Additional legacy smoke test migration:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin.py tests/test_checkin_endpoints.py -q
```

Result:

```text
10 passed in 1.02s
```

### Frontend RED

Command:

```bash
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts
```

Initial result before implementation:

```text
3 failed | 1 passed
```

Failures showed the expected missing behavior:

- `@/lib/api/checkin` did not exist.
- `@/components/checkin/checkin-screen` did not exist.
- `ProfileScreen` did not include the metrics-backed check-in statistics component.

### Frontend GREEN

Command:

```bash
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts
```

Result:

```text
4 passed, 18 passed tests
```

## Required Verification

### Contracts Generate

Command:

```bash
npm run contracts:generate
```

Result:

```text
wrote packages/contracts/openapi.json (99204 bytes)
contracts: regenerated openapi.json + _generated.ts
```

### Backend Endpoint Tests

Command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py -q
```

Result:

```text
7 passed in 0.67s
```

### Frontend Focused Tests

Command:

```bash
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx __tests__/hooks/useProfile.test.ts
```

Result:

```text
3 passed, 15 passed tests
```

Vitest also printed the existing Vite CJS deprecation warning.

### Contracts Check

First run before staging generated contract files failed because `contracts:check` compares generated artifacts against HEAD and the intentional check-in contract artifacts were not staged yet.

After explicit staging, rerun command:

```bash
npm run contracts:check
```

Result:

```text
wrote packages/contracts/openapi.json (99204 bytes)
contracts: regenerated openapi.json + _generated.ts
```

Exit code: 0.

## Additional Verification

Command:

```bash
pnpm exec tsc --noEmit
```

Result: exit code 0.

Command:

```bash
git diff --cached --check
```

Result: exit code 0.

Command:

```bash
git diff --cached --check
```

Result: exit code 0.

## Notes And Concerns

- `scripts/contracts/export_openapi.py` was changed and staged because otherwise regenerated check-in contracts would not be reproducible.
- `next-env.d.ts` was dirty before this task and remains unstaged.
- Payment/paywall behavior was not touched.
- Production service on port 3002 was not touched.

## Review Fixes

### Important Finding 1: Read Flow And Yesterday Echo

Fixed:

- `CheckinScreen` now calls real `getCheckin(targetDate)` before rendering the form.
- Existing check-ins render a saved state with the persisted values and an edit action.
- Read loading and read error states render explicitly and do not fall back to empty mock/demo data.
- `YesterdayEchoLoader` now calls real `getYesterdayCheckin()` and renders loading/error/empty/saved states through `YesterdayEchoBlock`.
- `TodayScreen` wires `YesterdayEchoLoader` only for local today.

RED evidence:

```text
CheckinScreen tests failed because loading/existing/error states and YesterdayEchoLoader did not exist.
```

GREEN evidence:

```text
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx
2 passed, 11 passed tests
```

### Important Finding 2: Yesterday CTA Target Date

Fixed:

- Yesterday CTA now routes to `/checkin?target=yesterday`.
- `/checkin` resolves `target=yesterday` with `resolveCheckinTargetDate(new Date(), profileTimezone, target)`.
- Date resolution uses local/profile timezone formatting, not UTC `toISOString().split("T")[0]`.
- Added tests for timezone-relative yesterday resolution and CTA routing.

### Important Finding 3: Current Streak Anchor

Fixed:

- `CheckinService.metrics()` now computes `currentStreak` relative to the query `to` date or local today fallback.
- If the latest check-in is older than the anchor date, current streak is `0`.
- Added backend regression test `test_metrics_current_streak_is_zero_when_latest_checkin_is_before_to_date`.

RED evidence:

```text
Expected currentStreak 0, got 2.
```

GREEN evidence:

```text
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py::test_metrics_current_streak_is_zero_when_latest_checkin_is_before_to_date -q
1 passed
```

### Minor Finding: Redundant Index

Fixed:

- Removed the redundant non-unique `(user_id, target_date)` index from `0017_extend_evening_checkins.py`.
- The existing unique constraint still supports the same lookup shape.

### Required Fix Verification

Command:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_checkin_endpoints.py tests/test_checkin.py -q
```

Result:

```text
11 passed in 1.14s
```

Command:

```bash
pnpm exec vitest run __tests__/api/checkin.test.ts __tests__/components/CheckinScreen.test.tsx __tests__/components/ProfileScreen.test.tsx __tests__/hooks/useProfile.test.ts
```

Result:

```text
4 passed, 22 passed tests
```

Vitest also printed the existing Vite CJS deprecation warning.

Command:

```bash
npm run contracts:check
```

Result:

```text
wrote packages/contracts/openapi.json (99204 bytes)
contracts: regenerated openapi.json + _generated.ts
```

Exit code: 0.

Command:

```bash
pnpm exec tsc --noEmit
```

Result: exit code 0.
