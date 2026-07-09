# Agent Report — Wave W3.4 Returns (Rework 02)

## Summary

Fixed P0 lunar enumeration, P1 solar residual enforcement, P1 structured current_location, P1 contract tests. Full verification gates run.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/returns.py` | Lunar: iterative crossing enumeration (no more offset probing); Solar: final residual enforced ≤0.001° |
| `apps/solarsage/solarsage/api/activation_layer.py` | `current_location` → structured `CurrentLocationRequest` Pydantic model |
| `apps/solarsage/tests/test_lunar_return.py` | 13 tests: August regression, strong index coverage, all debug fields required |
| `apps/solarsage/tests/test_solar_return.py` | 11 tests: all debug fields required, strong index coverage |
| `artifacts/audit/2026-07-08/20_sidecar_activation_layer_w3_4_returns.json` | Regenerated (unchanged) |

## Fixes

### P0: Lunar iterative enumeration
Replaced offset probing (`mooncross_ut` from fixed start points) with true iterative enumeration:
1. Start at `target_jd - 30.0`
2. Call `mooncross_ut`, collect candidate, advance `cursor = jd + epsilon`
3. Continue until crossing > target_jd or max iterations (50)
4. Select `max(candidate_jd)` with residual ≤ 0.001°

Fixed both regressions:
- July 16 target: `2461236.95` (was `2461209.52`)
- August 12 target: `2461264.38` (was `2461236.95`)

### P1: Solar residual enforced
After search and optional refinement, final residual check raises `ValueError` if > 0.001°.

### P1: Structured current_location
Replaced `dict | None` with `CurrentLocationRequest(BaseModel)` with `lat`, `lon`, `tz`. Malformed requests (missing `lat`/`lon`) now return 422 validation error instead of 500.

### P1: Strong index/debug tests
Every return activation verified:
- Present in appropriate `by_house`/`by_planet` index for its `target_type`
- All index refs point to valid activation IDs
- All 11 required debug fields present (`return_type`, `return_jd`, `return_utc_iso`, `target_jd`, `return_location_policy`, `return_location_source`, `return_location_reason`, `return_lat`, `return_lon`, `return_tz`, `resolved_house_system`)

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar targeted (all waves) | 96 passed, 1 warning |
| Sidecar full | 117 passed, 1 warning |
| API targeted | 28 passed |
| API full | 695 passed, 5 skipped, 1 warning |
| W3.4 artifact | 133 activations, wave=W3.4, 1 fallback warning |
| Hashseed × 3 (all identical) | `d78b174793f3...` |
| Combined W3.4 build time | 0.246s |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Relocation probe (verified)

```python
fallback warnings count = 1 ✓
relocated warnings = [] ✓
relocated location_source = current_location ✓
equator resolved = PLACIDUS ✓
fallback ids != relocated ids ✓
```

## Commit

`0b8ce6a`

## Push Status

`NOT_ATTEMPTED`
