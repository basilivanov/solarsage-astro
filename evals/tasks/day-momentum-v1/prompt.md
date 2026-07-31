# Eval task — Day support momentum v1

## Packet

- Phase / Wave: `EVAL-BACKEND-ALGO-V1`
- Modules: `M-DAY-RELATIVE-STATUS`, `M-SCHEMAS-DAY`, generated contracts
- Goal: add a deterministic support-momentum reading to the existing
  user-relative day status, reusing only data the function already receives.

Work autonomously in the provided repository. Do not use subagents or delegate
the task. Do not commit, push, install system packages, access secrets, or modify
files outside the exact write scope. Run the targeted checks before reporting.

## Required behavior

Extend `compute_relative_status` in
`apps/api/app/services/day_relative_status.py` and its read schema
`RelativeDayStatusRead` in `apps/api/app/schemas/day.py` with two fields:

- `momentum`: `"rising" | "flat" | "falling" | "insufficient"`;
- `momentumDelta`: number rounded to two decimal places, or `null` when the
  momentum is `insufficient`.

Momentum compares the user's recent support level with the days before it,
using only `today_support` and the already-passed `history`
(`history[0]` is yesterday, `history[1]` the day before, and so on):

- recent window: mean of `today_support` and `history[0].support`;
- previous window: mean of `history[1].support` and `history[2].support`;
- if `history` contains fewer than 3 entries, return `insufficient` and `null`;
- otherwise compute the raw difference (`recent - previous`):
  - `rising` when the raw difference is at least `+5.0`;
  - `falling` when it is at most `-5.0`;
  - `flat` otherwise.

Round only the returned delta; classification uses the unrounded difference.
Momentum is computed the same way in both `absolute` (cold start) and
`relative` modes — the mode logic itself must not change. Support values stay
on their existing 0–100 scale; do not z-score the momentum.

All existing fields, statuses, hysteresis, std floor, bands, markers, labels,
rounding, and camelCase wire serialization must remain unchanged. The two new
fields must appear in the wire contract as `momentum` and `momentumDelta`.

## Exact write scope

- `apps/api/app/schemas/day.py`
- `apps/api/app/services/day_relative_status.py`
- `apps/api/tests/test_day_relative_status.py`
- `packages/contracts/openapi.json`
- `packages/contracts/_generated.ts`
- `packages/contracts/_generated.zod.ts`
- `grace/verification-matrix.md`

## Required evidence

- Backend coverage for `rising`, `falling`, `flat`, `insufficient`, the exact
  `±5.0` boundaries (boundary value classifies, e.g. exactly `+5.0` is
  `rising`), a just-inside case (e.g. `+4.99` is `flat`), and proof that
  classification ignores rounding (a raw delta like `5.004` is `rising` while
  the reported delta is `5.0`).
- A case showing momentum works in absolute mode (history of 3–4 days).
- Regenerated shared contracts with camelCase wire names.
- GRACE contracts/maps kept accurate in every touched source file and the
  verification matrix updated for the new behavior.
- A final report listing changed files and the exact commands/results run.

## Frozen / out of scope

- Mode selection, hysteresis, absolute overrides, bands, markers and labels.
- The callers of `compute_relative_status` (Today pipeline) — the read schema
  change is additive; do not touch `today_service.py` or any other caller.
- Database schema, migrations, caching, pregeneration jobs.
- New dependencies, frontend rendering, production configuration and deploys.

## Verification

Run at least:

```bash
apps/api/.venv/bin/python -m pytest apps/api/tests/test_day_relative_status.py -q
npx tsc --noEmit
python3 scripts/grace_lint.py apps/api/app
git diff --check
```

Use `bash scripts/contracts/sync.sh` when regenerating contracts, but do not
broaden scope to repair unrelated pre-existing failures.

If correct implementation requires a file outside the exact write scope, stop
and report the missing scope instead of changing that file.
