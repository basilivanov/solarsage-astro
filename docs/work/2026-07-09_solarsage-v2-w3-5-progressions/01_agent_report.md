# Agent Report — Wave W3.5 Progressions

## Summary

Implemented `solar_arc` and `secondary_progression` activation-layer support in the sidecar. Uses day-for-year secondary progression model and progressed-Sun-based solar arc delta. `TodayService` remains unwired.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/progressions.py` | **New** — Solar arc + secondary progression service |
| `apps/solarsage/solarsage/services/activation_builder.py` | Added W3.5 techniques (solar_arc, secondary_progression) |
| `grace/canon/activation_rules.v1.yml` | Added `progression_base` strength keys (4 kinds) |
| `apps/solarsage/tests/test_solar_arc.py` | **New** — 7 solar arc tests |
| `apps/solarsage/tests/test_secondary_progressions.py` | **New** — 8 secondary progression tests |
| `apps/api/tests/test_activation_layer_progressions.py` | **New** — 6 API boundary tests for progressions |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Updated for W3.5 support |
| `apps/solarsage/tests/test_activation_transits.py` | Updated for W3.5 support |
| `apps/solarsage/tests/test_firdar.py` | Updated unsupported technique test |
| `scripts/audit_sidecar_activation.py` | Wave detection: W3.5 for progression techniques |
| `artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json` | **New** — W3.5 artifact (147 activations) |

## Secondary Progression Algorithm
```
age_years = (target_jd - birth_jd) / 365.2425
progressed_jd = birth_jd + age_years
progressed_positions = calculate_positions(progressed_jd)
```

Progressed Moon aspects against natal planets/angles/lots (max orb 1.0°).
Progressed Sun sign/house transitions when within 1.0° of boundary.

## Solar Arc Algorithm
```
solar_arc_delta = normalize(progressed_sun_lon - natal_sun_lon)
solar_arc_longitude(P) = normalize(natal_longitude(P) + solar_arc_delta)
```

SA planets to natal personal planets (SUN, MOON, MERCURY, VENUS, MARS), natal angles, natal lots.

## Canon Strengths

| Key | Value |
|-----|-------|
| `solar_arc_aspect` | 0.70 |
| `progressed_moon_aspect` | 0.65 |
| `progressed_sun_sign_transition` | 0.50 |
| `progressed_sun_house_transition` | 0.50 |

## Activation Counts (Basil W3.5 artifact, 147 total)

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
| solar_arc | 11 |
| secondary_progression | 3 |

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar targeted (all waves) | 115 passed, 1 warning |
| Sidecar full | 136 passed, 1 warning |
| API targeted | 34 passed |
| API full | 701 passed, 5 skipped, 1 warning |
| W3.5 artifact | 147 activations, wave=W3.5 |
| Hashseed × 3 | Identical |
| Combined W3.5 build time | 0.30s |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`887228c`

## Push Status

`NOT_ATTEMPTED`
