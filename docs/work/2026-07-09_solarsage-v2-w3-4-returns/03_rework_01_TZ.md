# W3.4 Rework 01 TZ — Return Location and Latest Lunar Return

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Push/deploy: do not push/deploy

Read first:

- `docs/work/2026-07-09_solarsage-v2-w3-4-returns/00_TZ.md`
- `docs/work/2026-07-09_solarsage-v2-w3-4-returns/02_arch_review.md`

## Goal

Fix W3.4 so the implementation satisfies the original return contract:

- return charts actually use `current_location` when supplied;
- lunar return is the latest valid crossing at or before target;
- requested house system is not silently ignored;
- tests prove these behaviors;
- audit artifact and report are regenerated.

No W3.5 work. No TodayService wiring. No scoring v2. No frontend. No push/deploy.

## Required Fixes

### 1. Separate natal inputs from return chart location

In `apps/solarsage/solarsage/services/returns.py`, keep birth data for natal Sun/Moon longitude lookup, but build return chart houses/ASC/MC using the resolved return location.

Recommended API shape:

```python
calculate_solar_return(
    birth_date=...,
    birth_time=...,
    birth_tz=...,
    birth_lat=...,
    birth_lon=...,
    target_year=...,
    house_system=...,
    return_lat=None,
    return_lon=None,
    return_tz=None,
)
```

Same for `calculate_lunar_return`. If return location is omitted, default to birth lat/lon/tz for backward compatibility. In `activation_builder.py`, pass `ret_lat`, `ret_lon`, and `ret_tz` into both return calculations.

Do not allow debug to claim `current_location` unless the chart was actually built with those coordinates.

### 2. Fix lunar latest-return selection

Replace residual-based selection with latest-JD selection:

- collect all candidate crossings in the search window;
- keep only `candidate_jd <= target_jd`;
- validate `target_jd - candidate_jd < 30`;
- validate longitude residual `<= 0.001°`;
- choose `max(candidate_jd)`;
- raise `ValueError` if no valid candidate exists.

Regression case required:

```text
birth: 1980-10-30 19:50 Europe/Moscow, lat=67.9394 lon=32.8144
target: 2026-07-16 12:00 Europe/Moscow
expected latest lunar return: 2461236.9515122585 approximately
current broken result: 2461209.5210913573
```

Use a sensible tolerance. Do not hardcode this result in production code.

### 3. Stop silently ignoring `house_system`

Extend `calculate_houses_cusps` backward-compatibly:

```python
calculate_houses_cusps(jd, lat, lon, house_system="PLACIDUS")
```

Minimum supported mapping:

- `PLACIDUS` -> Swiss Ephemeris `b"P"`;
- `WHOLE_SIGN` -> Swiss Ephemeris `b"W"`.

Preserve existing high-latitude behavior: if requested `PLACIDUS` and `abs(lat) >= 60`, resolve to `WHOLE_SIGN`. Expose the resolved value as before. If another house system is requested and not supported, fail clearly with `ValueError`; do not silently use Placidus.

Update all callers to pass the requested house system where available.

### 4. Strength strictness tests

Add focused tests proving missing return strength keys raise `KeyError`:

- missing `solar_return_angle_in_natal_house` or another required solar key;
- missing `lunar_return_moon_house` or another required lunar key.

Keep `_get_return_strength` strict. Do not add `.get(..., default_strength)` fallback.

### 5. Strengthen contract tests

Add or update tests so they fail on the current broken implementation:

- explicit `current_location` changes actual return chart houses/ASC/MC, not only debug fields;
- endpoint with current location at low latitude resolves return house system as `PLACIDUS` when requested `PLACIDUS`;
- no fallback warning is emitted when `current_location` is supplied;
- fallback warning is emitted exactly once when absent;
- lunar return for `2026-07-16` uses the latest candidate `2461236.9515122585` rather than the previous cycle;
- every return activation debug contains all required fields from `00_TZ.md`;
- all return index refs point to existing IDs, and every return activation is present in the appropriate index for its target type;
- API boundary fixture includes all required return debug fields and preserves them;
- no TodayService wiring change: `sidecar_activation_layer=None` remains present.

### 6. Regenerate artifact and report

Regenerate:

```text
artifacts/audit/2026-07-08/20_sidecar_activation_layer_w3_4_returns.json
```

Update:

```text
docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md
```

The report must include:

- the corrected location behavior;
- lunar latest-return proof;
- Basil solar return fixture comparison;
- exact verification command results;
- audit activation count by technique;
- hashseed SHA values;
- combined W3.4 build elapsed wall time;
- `sidecar_activation_layer=None` proof;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Required Verification

Run the full required command list from `00_TZ.md`, plus the new regression tests above.

Also run these focused probes and include their result in the report:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_solar_return.py \
  tests/test_lunar_return.py -q
```

```bash
python3 - <<'PY'
from fastapi.testclient import TestClient
from solarsage.app import app

client = TestClient(app)
base = {
    "birth": {
        "date": "1980-10-30",
        "time": "19:50",
        "lat": 67.9394,
        "lon": 32.8144,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-07-08",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": ["solar_return", "lunar_return"],
}

fallback = client.post("/v1/activation-layer", json=base).json()["activation_layer"]
relocated = client.post(
    "/v1/activation-layer",
    json={**base, "current_location": {"lat": 0.0, "lon": 0.0, "tz": "UTC"}},
).json()["activation_layer"]

assert fallback["warnings"].count(
    "return_location_fallback:birth_location:current_location_missing"
) == 1
assert relocated["warnings"] == []
assert all(
    item["debug"]["return_location_source"] == "current_location"
    for item in relocated["activations"]
    if item["technique"] in {"solar_return", "lunar_return"}
)
assert any(
    item["debug"]["resolved_house_system"] == "PLACIDUS"
    for item in relocated["activations"]
    if item["technique"] in {"solar_return", "lunar_return"}
)
assert [a["id"] for a in fallback["activations"]] != [a["id"] for a in relocated["activations"]]
print("relocation_probe_ok")
PY
```

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.4 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-4-returns/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-4-returns/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
