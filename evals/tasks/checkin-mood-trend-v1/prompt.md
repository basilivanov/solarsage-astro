# Eval task — Check-in mood trend v1

## Packet

- Phase / Wave: `EVAL-FULLSTACK-V1`
- Modules: `M-SCHEMAS-CHECKIN`, `M-CHECKIN-SERVICE`,
  `M-PROFILE-CHECKIN-STATS-CARD`, generated contracts
- Goal: add a truthful two-week mood trend to the existing check-in metrics API
  and Profile card.

Work autonomously in the provided repository. Do not use subagents or delegate
the task. Do not commit, push, install system packages, access secrets, or modify
files outside the exact write scope. Run the targeted checks before reporting.

## Required behavior

Extend `GET /api/checkin/metrics` with:

- `moodTrend`: `"up" | "steady" | "down" | "insufficient"`;
- `moodTrendDelta`: number rounded to two decimal places, or `null` when the
  trend is `insufficient`.

Use the endpoint's resolved upper date as the anchor:

- current window: `upper - 6 days` through `upper`, inclusive;
- previous window: `upper - 13 days` through `upper - 7 days`, inclusive.

Use only rows already selected by the existing `from` / `to` range. Do not
widen the database query for the trend. If either window contains fewer than
three check-ins, return `insufficient` and `null`. Otherwise calculate the two
mean moods and their raw difference (`current - previous`):

- `up` when the raw difference is at least `+0.5`;
- `down` when it is at most `-0.5`;
- `steady` otherwise.

Round only the returned delta; classification uses the unrounded difference.
All existing totals, distributions, averages, streaks, query semantics and
camelCase serialization must remain unchanged.

Render the new value in `CheckinStatsCard` with the exact public labels:

- `up` → `Настроение: растёт`;
- `steady` → `Настроение: стабильно`;
- `down` → `Настроение: снижается`;
- `insufficient` → `Настроение: мало данных`.

The rendered block must have `data-testid="checkin-mood-trend"` and
`data-trend` equal to the wire enum. Preserve the current loading, fail-open,
streak and milestone behavior.

## Exact write scope

- `apps/api/app/schemas/checkin.py`
- `apps/api/app/services/checkin_service.py`
- `apps/api/tests/test_checkin_endpoints.py`
- `components/profile/checkin-stats-card.tsx`
- `__tests__/components/CheckinStatsCard.test.tsx`
- `packages/contracts/openapi.json`
- `packages/contracts/_generated.ts`
- `packages/contracts/_generated.zod.ts`
- `grace/verification-matrix.md`

## Required evidence

- Backend coverage for up, down, steady, insufficient and the exact `±0.5`
  boundaries, including a `from` range that truncates a window.
- Frontend coverage for all four labels and their stable DOM attributes.
- Regenerated shared contracts with camelCase wire names.
- GRACE contracts/maps kept accurate in every touched source file and the
  verification matrix updated for the new behavior.
- A final report listing changed files and the exact commands/results run.

## Frozen / out of scope

- Database schema and migrations.
- Check-in creation, yesterday flow, streak semantics and API authentication.
- Today/convergence implementation and documents.
- Styling redesign beyond the small trend row.
- New dependencies, fallback mock data, production configuration and deploys.

## Verification

Run at least:

```bash
apps/api/.venv/bin/python -m pytest apps/api/tests/test_checkin_endpoints.py -q
npx vitest run __tests__/components/CheckinStatsCard.test.tsx __tests__/api/checkin.test.ts
npx tsc --noEmit
python3 scripts/grace_lint.py apps/api/app
git diff --check
```

Use `bash scripts/contracts/sync.sh` when regenerating contracts, but do not
broaden scope to repair unrelated pre-existing failures.

If correct implementation requires a file outside the exact write scope, stop
and report the missing scope instead of changing that file.
