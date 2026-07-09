# Agent Report — Wave W3.4 Returns

## Summary

Implemented `solar_return` and `lunar_return` activation-layer support in the sidecar. Uses Swiss Ephemeris `solcross_ut`/`mooncross_ut` for exact return moment search. `TodayService` remains unwired.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/returns.py` | **New** — Solar/lunar return service: crossing search, return chart, ASC/MC, Moon house |
| `apps/solarsage/solarsage/services/activation_builder.py` | Added W3.4 techniques (solar_return, lunar_return); current_location param; return activation logic |
| `apps/solarsage/solarsage/api/activation_layer.py` | Added `current_location` field to request schema |
| `grace/canon/activation_rules.v1.yml` | Added `return_base` strength keys (7 kinds) |
| `apps/solarsage/tests/test_solar_return.py` | **New** — 9 solar return tests |
| `apps/solarsage/tests/test_lunar_return.py` | **New** — 9 lunar return tests |
| `apps/api/tests/test_activation_layer_returns.py` | **New** — 5 API boundary tests for return activations |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Updated for return technique support |
| `apps/solarsage/tests/test_activation_transits.py` | Updated for return technique support |
| `apps/solarsage/tests/test_firdar.py` | Updated unsupported technique test |
| `scripts/audit_sidecar_activation.py` | Wave detection: W3.4 for return techniques |
| `artifacts/audit/2026-07-08/20_sidecar_activation_layer_w3_4_returns.json` | **New** — W3.4 artifact (133 activations) |

## Return Search Algorithm

### Solar return
- Natal Sun longitude from natal chart
- `solcross_ut(natal_sun_lon, birthday_noon_minus_3d, FLG_SWIEPH)` → exact crossing JD
- Longitude residual after search: verified ≤ 0.001°
- Basil 2026 return JD: `2461344.345224213` (fixture: `2461344.3452186584`, diff: 5.5e-06°)
- Return chart: planets, houses, ASC, MC at return JD

### Lunar return
- Natal Moon longitude from natal chart
- Search `mooncross_ut(natal_moon_lon, target_jd - 28.0 + offsets, FLG_SWIEPH)` across multiple offsets
- Pick the crossing with smallest longitude residual that is ≤ target_jd
- Constraints: `return_jd ≤ target_jd`, `target_jd - return_jd < 30 days`
- Basil 2026-07-08 return JD: `2461209.5210913573` (June 18, 2026), residual < 0.001°

## Location Policy

`current_location_if_known_else_birth_location`:
- If `current_location` supplied in request: use it for return chart houses
- If absent: use birth location, add one deterministic warning: `return_location_fallback:birth_location:current_location_missing`

## Canon Strengths

| Key | Value |
|-----|-------|
| `solar_return_angle_in_natal_house` | 0.70 |
| `solar_return_chart_ruler` | 0.70 |
| `solar_return_moon_house` | 0.65 |
| `solar_return_angular_planet` | 0.60 |
| `lunar_return_angle_in_natal_house` | 0.55 |
| `lunar_return_moon_house` | 0.60 |
| `lunar_return_angular_planet` | 0.50 |

## Activation Counts (Basil W3.4 artifact, 133 total)

| Technique | Count |
|-----------|-------|
| transit_to_natal | 50 |
| transit_to_angle | 16 |
| transit_planet_in_house | 10 |
| transit_to_lot | 35 |
| annual_profection | 2 |
| monthly_profection | 2 |
| firdar_major | 1 |
| firdar_minor | 1 |
| solar_return | 9 |
| lunar_return | 7 |

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar targeted (all active waves) | 90 passed, 1 warning |
| Sidecar full | 111 passed, 1 warning |
| API targeted | 28 passed |
| API full | 695 passed, 5 skipped, 1 warning |
| W3.4 artifact | 133 activations, wave=W3.4, no unsupported techniques |
| Hashseed × 3 | Identical |
| Fallback warning count | exactly 1 |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
