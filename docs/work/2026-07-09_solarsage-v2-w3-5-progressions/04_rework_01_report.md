# Rework 01 Report — Wave W3.5 Progressions

## Summary

Fixed P0 strength formula, P1 per-technique orb, P1 debug contract, P1 Sun transition coverage, P2 uppercase SA IDs, P2 shared aspect canon.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/progressions.py` | Per-technique orb lookup; canon-based strength; full debug keys; transition base_strength/orb_factor |
| `apps/solarsage/solarsage/services/activation_builder.py` | Uppercase SA IDs; source_longitude in SA debug |
| `apps/solarsage/tests/test_solar_arc.py` | 10 tests (up from 7): missing orb keys, shared aspect canon |
| `apps/solarsage/tests/test_secondary_progressions.py` | 11 tests (up from 8): sign/house/wrap Sun transitions |
| `artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json` | Regenerated |

## Fixes

### P0: Canon strength formula
`_check_and_add_aspect` now accepts `base_strength` parameter. Formula: `strength = round(min(1.0, base_strength * orb_factor), 4)`. Hardcoded `0.7` removed. All 14 W3.5 artifact activations verified: `strength == round(debug.base_strength * debug.orb_factor, 4)`.

### P1: Per-technique orb lookup
`_get_progression_orb("solar_arc")` reads `techniques.solar_arc.orb`.
`_get_progression_orb("secondary_progression")` reads `techniques.secondary_progression.orb`.
Missing/non-numeric raises `KeyError`.

### P1: Debug contract
All aspect activations include `source_longitude`, `target_longitude`, `angular_distance`, `aspect_angle`, `orb`, `orb_factor`, `base_strength`. Sun transitions include all TZ keys with `None` where not applicable.

### P1: Sun transition coverage
Added `test_progressed_sun_sign_transition`, `test_progressed_sun_house_transition`, `test_sun_transition_wrap_around`.

### P2: Solar arc IDs uppercase
IDs use uppercase source keys (e.g., `solar_arc__MARS__TRINE__NATAL_VENUS`).
Evidence remains human-readable (`Solar Arc Mars trine natal Venus`).

### P2: Shared aspect canon
`test_progression_aspects_match_builder_map` proves `progression.ASPECT_ANGLES == builder.ASPECT_ANGLES`.

## Verification

| Gate | Result |
|------|--------|
| Sidecar targeted progression+others | 97 passed |
| Sidecar full | 142 passed, 1 warning |
| API targeted | 34 passed |
| API full | 701 passed, 5 skipped, 1 warning |
| Artifact strength formula | All 14 progression activations verified |
| SA IDs uppercase | All SA IDs pass `source == source.upper()` |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
