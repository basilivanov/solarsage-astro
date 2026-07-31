# P1-G TZ — strict birth-time canon and mode-aware calculation plan

Date: 2026-07-31
Status: implementation packet
Depends on: P1-A..F, packet 25 / commit `dd88eb57`.

## 1. Goal

Close the missing production boundary between persisted profile mode and the
later sidecar/convergence adapter. Add one strict, immutable calculation plan
for `exact | bucket | unknown`, derived only from the frozen W1 canon.

This packet does **not** calculate a chart or silently replace the legacy
Today/Calendar call graph. It makes the correct control ranges and capabilities
available to the next sidecar/robustness packet, with no invented noon.

## 2. Exact write scope

Only these paths may be created/changed:

1. `apps/api/app/services/today_convergence_canon.py`;
2. `apps/api/app/services/today_birth_time.py` (new);
3. `apps/api/tests/test_today_convergence_canon.py`;
4. `apps/api/tests/test_today_birth_time.py` (new);
5. `grace/verification-matrix.md`;
6. `grace/knowledge-graph.xml`;
7. this reviewer-owned packet — do not edit it.

If another file is needed, stop and report. Coder does not commit or push.

## 3. Strict canon extraction

Extend the existing immutable `TodayConvergenceCanon`; do not modify
`grace/canon/today_convergence.v1.yml` and do not import `analysis/`.

Add typed frozen records for the complete existing `birth_time` section:

- modes, exactly `exact, bucket, unknown` in this order;
- bucket ranges, exactly:
  - night `[0, 6)`;
  - morning `[6, 12)`;
  - day `[12, 18)`;
  - evening `[18, 24)`;
- control-grid rules, exactly `edges_plus_middle` and
  `every_4h_plus_2359`;
- orb-margin rule, gap hours, formula and sparse/oracle gate exactly as stored;
- capabilities for all three modes, including the separate `angles` flag;
- migration mapping, exactly `null_birth_time: unknown` and
  `non_null: exact`.

Validate exact key sets, booleans, integer ranges, non-overlap/full-day bucket
coverage and frozen literal values. Any drift raises
`TodayConvergenceCanonError` with stable
`today_convergence_canon:birth_time_*` reason. Expose immutable mappings/tuples;
no mutable nested dict may escape.

Do not duplicate or hard-code the seven control times in the canon loader. The
resolver derives them from the validated symbolic rules, bucket bounds and
gap hours.

## 4. Mode-aware resolver

Create a pure module with frozen records and no DB, HTTP, sidecar, logging or
wire/Pydantic dependency:

```python
resolve_birth_time(
    *,
    mode: object,
    birth_time: datetime.time | None,
    bucket: object | None,
    canon: TodayConvergenceCanon | None = None,
) -> BirthTimeResolution

resolve_profile_birth_time(
    profile: BirthTimeProfileLike,
    canon: TodayConvergenceCanon | None = None,
) -> BirthTimeResolution
```

`BirthTimeResolution` owns:

- `mode: exact|bucket|unknown`;
- `bucket: night|morning|day|evening|None`;
- `birth_time: HH:MM|None` (present only for exact);
- `range_start`, `range_end` as canonical `HH:MM` strings; `24:00` is allowed
  only as the excluded right boundary;
- ordered `control_times: tuple[str, ...]` used for sidecar calculations;
- `canonical_gap_hours: int | None` (`None` for an exact point);
- frozen capabilities `{houses, angles, lots, exact_timing}`.

Canonical derivation:

- exact: one control time equal to the persisted minute; equal start/end;
- bucket: start, arithmetic midpoint, and `end - 1 minute`;
- unknown: every canonical gap from `00:00` through `20:00`, plus `23:59`;
- bucket/unknown capabilities are all false; exact capabilities are all true.

Valid shapes are exactly the profile contract:

- exact requires `datetime.time` and null bucket;
- bucket requires null time and one canonical bucket;
- unknown requires null time and null bucket.

Reject seconds/microseconds in exact time rather than truncating them. Reject
unknown modes, non-string buckets, invalid combinations, or malformed profile
objects with stable `TodayBirthTimeError` reasons prefixed
`today_birth_time:`. Do not infer mode from time presence. Do not use a
fallback value, especially `birth_time or "12:00"`.

The returned plan is calculation input and cache/snapshot identity material;
it must be deterministic and fully frozen. It contains no UX dismiss flag.

## 5. Required tests

1. Loader exposes the entire frozen birth-time block and nested records/maps
   cannot be mutated.
2. A copied canon with a changed/missing mode, bucket boundary, grid rule,
   gap, formula, gate, capability/angles value, or migration value fails with
   a stable birth-time canon reason.
3. Exact time returns one identical point/range and all capabilities true.
4. All four buckets return the exact W1 grids:
   `00:00/03:00/05:59`, `06:00/09:00/11:59`,
   `12:00/15:00/17:59`, `18:00/21:00/23:59`.
5. Unknown returns
   `00:00,04:00,08:00,12:00,16:00,20:00,23:59`, range `[00:00,24:00)`,
   and no capabilities.
6. Every invalid state combination fails before producing a plan; exact with
   seconds/microseconds fails rather than silently rounding.
7. `resolve_profile_birth_time` is byte/value-identical to the field-level
   resolver and fails safely when required attributes are absent.
8. Results and nested capabilities are frozen, input case/whitespace is not
   silently normalized into another valid persisted state, and no legacy
   aliases exist.
9. Source guard proves the new module imports no `analysis` code and contains
   no executable noon fallback expression.

## 6. GRACE and verification

Register `M-TODAY-BIRTH-TIME`, its edge to
`M-TODAY-CONVERGENCE-CANON`, and a `UC-TODAY-BIRTH-TIME-PLAN` row.

Run:

```bash
cd apps/api
/opt/solarsage-astro/apps/api/.venv/bin/python -m pytest \
  tests/test_today_convergence_canon.py \
  tests/test_today_birth_time.py -q
cd ../..
/opt/solarsage-astro/apps/api/.venv/bin/python -m ruff check \
  apps/api/app/services/today_convergence_canon.py \
  apps/api/app/services/today_birth_time.py \
  apps/api/tests/test_today_convergence_canon.py \
  apps/api/tests/test_today_birth_time.py
python3 scripts/grace_lint.py apps/api/app --quiet
bash scripts/grace/check-markers.sh
git diff --check
```

Report exact test counts, derived grids/capabilities, invalid reason examples,
and exact changed paths.

## 7. Out of scope / next packet

- no edits to frozen W1 YAML or thresholds;
- no sidecar multi-control request yet;
- no cross-control evidence merge/orb-margin/sect gate yet;
- no ActivationEvidence → RawPhysicalFact adapter;
- no Today/Calendar cutover, noon-fallback deletion or natal readiness change
  until robust calculation is atomically available;
- no profile hash/cache/snapshot/wire/frontend change;
- no LLM, pregen, persistence or deployment.

The next packet consumes this plan to calculate all control points and perform
the fail-closed robustness intersection. Only that accepted path may replace
the legacy noon fallback.
