# Rework 01 Report — Wave W3.6 Eclipse Window

## Summary

Fixed P1 nearest-candidate contract, P2 default support test, added regression. The `eclipse_window` now activates only from the single nearest eclipse candidate.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/eclipses.py` | `find_eclipses()` builds activations from exactly one nearest candidate (`candidates[:1]`) |
| `apps/solarsage/tests/test_eclipse_window.py` | Added `test_nearest_eclipse_only_basil_mar03` — proves fix for far-eclipse false positive |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Default-all test imports `ALL_TECHNIQUES`/`SUPPORTED_ORDER` from builder for contract-complete coverage |

## Fixes

### P1: Only nearest eclipse candidate used
`find_eclipses()` now builds activations from `candidates[0]` (the nearest after sorting by `abs_delta`, `eclipse_jd`, `eclipse_kind`). No farther eclipse candidate is activated even if it has natal hits.

### P2: Default support test
Uses `from solarsage.services.activation_builder import ALL_TECHNIQUES, SUPPORTED_ORDER` and asserts the full W3.1-W3.6 deterministic default order. No longer relies on incidental activation presence for contract coverage.

### Regression: Basil 2026-03-03
Nearest candidate is the lunar eclipse on 2026-03-03 (days_delta=0.1). Since it has no Basil natal/angle/lot hits within orb, zero activations emitted. Test passes after fix, would fail against original code.

## Verification

| Gate | Result |
|------|--------|
| Sidecar targeted | 114 passed |
| Sidecar full | 159 passed, 1 warning |
| API targeted | 38 passed |
| API full | 705 passed, 5 skipped, 1 warning |
| Artifact (151) | Still has 1 eclipse_window activation |
| Hashseed × 3 | Identical |
| Mar 03 regression | 0 activations (correct) |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`2346d1c`

## Push Status

`NOT_ATTEMPTED`
