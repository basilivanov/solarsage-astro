# Agent Report — Wave W3.6 Eclipse Window

## Summary

Implemented `eclipse_window` activation-layer support in the sidecar. Uses Swiss Ephemeris `sol_eclipse_when_glob`/`lun_eclipse_when` to find nearest eclipses within a configured window. `TodayService` remains unwired.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/eclipses.py` | **New** — Eclipse search + conjunction activation generation |
| `apps/solarsage/solarsage/services/activation_builder.py` | Added `eclipse_window` to W3.6 techniques |
| `grace/canon/activation_rules.v1.yml` | Added `days_before`, `days_after`, `orb_to_natal`, `strength` keys |
| `apps/solarsage/tests/test_eclipse_window.py` | **New** — 12 eclipse tests |
| `apps/api/tests/test_activation_layer_eclipse.py` | **New** — 4 API boundary tests |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Updated for W3.6 |
| `apps/solarsage/tests/test_activation_transits.py` | Updated for W3.6 |
| `apps/solarsage/tests/test_firdar.py` | Updated unsupported technique test |
| `scripts/audit_sidecar_activation.py` | Wave detection: W3.6 |
| `artifacts/audit/2026-08-12/22_sidecar_activation_layer_w3_6_eclipse.json` | **New** — W3.6 artifact (151 activations) |

## Eclipse Calculation

Uses Swiss Ephemeris:
- `sol_eclipse_when_glob(target_jd, flags, 0, backwards)` for solar eclipses
- `lun_eclipse_when(target_jd, flags, 0, backwards)` for lunar eclipses

Collects forward and backward candidates, filters by `days_before`/`days_after` window, sorts by nearest `abs_delta`. Type mapped from retflag constants. Longitude taken at maximum eclipse.

## Canon Config

| Key | Value |
|-----|-------|
| `days_before` | 14 |
| `days_after` | 14 |
| `orb_to_natal` | 3.0 |
| `strength` | 0.55 |

## Activation Shape

- Aspect: conjunction
- Polarity: mixed
- Phase: period
- Targets: natal planets, angles (ASC/DSC/MC/IC), all 7 Hermetic lots
- Strength: `base_strength * orb_factor * window_factor`

## Artifact Count (Basil 2026-08-12, 151 total)

1 eclipse_window activation. All debug fields validated: kind/type/retflag/jd/date/delta/longitudes/orb/factors.

## Verification

| Gate | Result |
|------|--------|
| Sidecar targeted | 88 passed |
| Sidecar full | 158 passed, 1 warning |
| API targeted | 38 passed |
| API full | 705 passed, 5 skipped, 1 warning |
| Artifact (151 activations) | wave=W3.6, 1 eclipse activation |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`97d9c3e`

## Push Status

`NOT_ATTEMPTED`
