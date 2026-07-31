# Eval task — Sidecar planet house v1

## Packet

- Phase / Wave: `EVAL-CROSSCODEBASE-V1`
- Modules: SolarSage sidecar natal pipeline, `M-NORMALIZATION-SERVICE`,
  natal context service
- Goal: the SolarSage sidecar starts emitting each natal planet's house; the
  API consumes it with a backward-compatible fallback.

Work autonomously in the provided repository. Do not use subagents or delegate
the task. Do not commit, push, install system packages, access secrets, or modify
files outside the exact write scope. Run the targeted checks before reporting.

## Background

The sidecar natal response returns `planets` (name, longitude, latitude,
speed, sign, retrograde) and `houses` (number, cusp, sign) as separate lists.
The API's `NormalizationService` therefore recomputes each planet's house from
its longitude via `find_house` (`apps/api/app/services/astro_utils.py`).
This duplicated mapping is recorded as technical debt in `AGENTS.md`.

## Required behavior

### Sidecar (`apps/solarsage`)

- Every planet in the natal response gains a `house` field: the integer house
  number (1–12) whose cusp interval contains the planet's longitude, using the
  same wraparound interval semantics as the API's `find_house`, or `null`
  when houses are unavailable for the chart.
- The computation lives in the sidecar's natal calculation path, not in the
  HTTP layer; existing response fields and the `houses` list stay unchanged.
- Both house systems already supported must produce correct `house` values.

### API (`apps/api`)

- `NormalizationService._planets_in_houses` prefers a planet's `house` value
  when the incoming natal payload provides a valid one (integer 1–12), and
  otherwise falls back to the existing `find_house(longitude, houses)`
  mapping. Charts produced by an old sidecar (no `house` field) must behave
  exactly as before.
- The natal context path (`natal_context_service.py`) must pass the new field
  through validation/serialization without dropping it; cached contexts
  created before this change (no `house`) remain valid and fall back.

### Out of scope for this change

Transit-to-natal house mapping (`find_house` on natal houses for transiting
planets) stays exactly as-is — do not change transit semantics.

## Exact write scope

- `apps/solarsage/solarsage/schemas/natal.py`
- `apps/solarsage/solarsage/models/chart.py`
- `apps/solarsage/solarsage/services/natal.py`
- `apps/solarsage/solarsage/services/calculation_core.py`
- `apps/solarsage/solarsage/api/natal.py`
- `apps/solarsage/tests/**`
- `apps/api/app/services/normalization_service.py`
- `apps/api/app/services/natal_context_service.py`
- `apps/api/tests/test_normalization_planet_house.py`
- `grace/verification-matrix.md`

## Required evidence

- A new sidecar test file `apps/solarsage/tests/test_planet_house.py`:
  every planet carries `house`; values match cusp intervals including the
  12th/1st-house wraparound; both supported house systems covered.
- A new API test file `apps/api/tests/test_normalization_planet_house.py`:
  preference for a provided valid `house`; fallback when the field is absent
  (old sidecar payload); fallback when the value is invalid (e.g. `0`,
  `13`, wrong type).
- All pre-existing sidecar natal tests stay green.
- GRACE contracts/maps kept accurate in every touched source file and the
  verification matrix updated for the new behavior.
- A final report listing changed files and the exact commands/results run.

## Frozen / out of scope

- Transit endpoints and transit-to-natal house semantics; synastry; lunar.
- Database schema and migrations; cache invalidation of existing contexts.
- API response schemas exposed to the frontend; generated contracts.
- New dependencies, deploys, systemd/docker configuration.

## Verification

Run at least:

```bash
export PYTHONPATH=apps/solarsage  # worktree code must shadow the venv's editable install
apps/solarsage/.venv/bin/python -m pytest apps/solarsage/tests/test_natal.py -q
apps/solarsage/.venv/bin/python -m pytest apps/solarsage/tests/test_planet_house.py -q
apps/api/.venv/bin/python -m pytest apps/api/tests/test_normalization_planet_house.py -q
python3 scripts/grace_lint.py apps/api/app
git diff --check
```

If correct implementation requires a file outside the exact write scope, stop
and report the missing scope instead of changing that file.
