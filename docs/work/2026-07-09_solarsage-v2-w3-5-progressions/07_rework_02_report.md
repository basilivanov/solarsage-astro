# Rework 02 Report — Wave W3.5 Progressions

## Summary

Closed remaining Rework 01 gaps: full transition debug in ActivationEvidence, deterministic transition tests, removed aspect canon duplication, non-numeric orb tests, and committed the regenerated artifact.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/progressions.py` | Import ASPECT_ANGLES/_classify_polarity from builder (no duplication) |
| `apps/solarsage/solarsage/services/activation_builder.py` | Full transition debug keys (all 13 fields) passed through to ActivationEvidence |
| `apps/solarsage/tests/test_solar_arc.py` | 13 tests (up from 10): non-numeric orb parametrized test; shared identity assertion |
| `apps/solarsage/tests/test_secondary_progressions.py` | 15 tests (up from 11): deterministic direct-style tests with fake contexts and monkeypatch builder tests |
| `artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json` | Regenerated and committed |

## Fixes

### P0: Artifact committed
The regenerated artifact with uppercase SA IDs, source_longitude, and corrected strengths is now included in the commit.

### P1: Full transition debug
Builder now passes through all 13 transition debug keys from the helper: `transition_type`, `current_sign`, `previous_sign`, `next_sign`, `current_house`, `target_house`, `boundary_longitude`, `distance_to_boundary`, `base_strength`, `orb_factor`. Non-applicable fields use `None`.

### P1: Deterministic transition tests
Replaced conditional tests with 5 deterministic tests:
- `test_progressed_sun_sign_transition_direct` — fake context at 29.5°
- `test_progressed_sun_house_transition_direct` — monkeypatched house cusp
- `test_sun_transition_wrap_around_direct` — fake context at 359.5°
- `test_sun_transition_builder_sign` — monkeypatched transitions, asserts full debug
- `test_sun_transition_builder_house` — monkeypatched transitions, asserts house debug

### P2: Aspect canon duplication removed
`progressions.py` imports `ASPECT_ANGLES` and `_classify_polarity` from `activation_builder.py`. Test proves `prog_angles is build_angles` (same object).

### P2: Non-numeric orb tests
`test_non_numeric_orb_raises` parametrized over both `solar_arc` and `secondary_progression` with `orb = "bad"`. Both raise `KeyError`/`ValueError`.

## Verification

| Gate | Result |
|------|--------|
| Sidecar targeted | 101 passed |
| Sidecar full | 146 passed, 1 warning |
| API targeted | 34 passed |
| API full | 701 passed, 5 skipped, 1 warning |
| Artifact verification | 14 progression activations, strength formula OK, uppercase IDs OK |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Working tree | Clean (except pre-existing untracked) |

## Commit

`44c7f7a`

## Push Status

`NOT_ATTEMPTED`
