# W3.4 Rework 02 TZ — Robust Lunar Scan and Contract Closure

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push/deploy

Read first:

- `docs/work/2026-07-09_solarsage-v2-w3-4-returns/00_TZ.md`
- `docs/work/2026-07-09_solarsage-v2-w3-4-returns/04_rework_01_review.md`

## Goal

Close the remaining W3.4 contract gaps:

- lunar return must be latest for every target, not only the tested July case;
- solar return precision invariant must be enforced;
- `current_location` request must be structured;
- required full verification/reporting must be complete.

No W3.5. No TodayService wiring. No scoring v2. No frontend. No push/deploy.

## Required Fixes

### 1. Replace lunar offset probing with iterative crossing enumeration

Do not solve this by adding more offsets.

Implement robust logic in `calculate_lunar_return`:

1. Set `search_start = target_jd - 30.0` or slightly earlier.
2. Call `swe.mooncross_ut(natal_moon_lon, cursor, flags)`.
3. If returned `jd > target_jd`, stop.
4. If returned `jd <= target_jd`, compute residual and collect it if residual `<= 0.001`.
5. Advance `cursor = jd + epsilon` where epsilon is enough to avoid returning the same crossing again.
6. Continue until the next crossing is after target, or until a hard iteration cap is reached.
7. Choose `max(candidate_jd)`.
8. Require `target_jd - return_jd < 30`.
9. Raise `ValueError` if no valid candidate exists.

The residual validates precision. It must not be the selection key.

### 2. Add regression for the missed August case

Add a test that fails on Rework 01:

```text
birth: 1980-10-30 19:50 Europe/Moscow, lat=67.9394 lon=32.8144
target: 2026-08-12 12:00 Europe/Moscow
expected latest lunar return: 2461264.375656118 approximately
broken Rework 01 result: 2461236.9515122585
```

Keep the existing `2026-07-16` regression too.

Prefer a helper in tests that independently scans crossings, or document the expected fixture values clearly. Do not hardcode expected JDs in production code.

### 3. Enforce solar residual threshold

After final solar return search/refinement:

- compute final residual;
- if residual `> 0.001`, raise `ValueError`;
- keep existing Basil fixture comparison test.

### 4. Make `current_location` a structured request model

In `apps/solarsage/solarsage/api/activation_layer.py`, replace untyped `dict | None` with a Pydantic model, for example:

```python
class CurrentLocationRequest(BaseModel):
    lat: float
    lon: float
    tz: str | None = None
```

Then pass a plain dict or model-dumped object to the builder consistently.

Add tests:

- valid `current_location` still works;
- malformed `current_location` missing `lat` or `lon` returns request validation error, not internal 500.

### 5. Finish the missing contract tests

Add/update tests so they assert:

- every return activation debug contains all fields required by `00_TZ.md`;
- every return activation index reference points to an existing ID;
- every return activation is present in the appropriate index for its target type;
- `sidecar_activation_layer=None` remains unchanged in `TodayService`.

Do not leave the old no-op index loops in place as the only index tests.

### 6. Full verification and report

Run and report the exact command results from `00_TZ.md`, including:

- sidecar targeted;
- sidecar full;
- API targeted;
- API full;
- audit artifact regeneration;
- three hashseed SHA values;
- artifact assertion script;
- relocation probe from Rework 01;
- `sidecar_activation_layer=None` proof;
- `git diff ... --check`;
- `git show --check HEAD`;
- `git status --short --branch`.

Also include combined W3.4 build elapsed wall time in the report.

Update:

```text
docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md
```

Commit all intended changes. Push status must remain `NOT_ATTEMPTED`.

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.4 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-4-returns/04_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-4-returns/05_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
