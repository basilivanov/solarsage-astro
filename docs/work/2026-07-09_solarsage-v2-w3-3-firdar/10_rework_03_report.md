# Rework 03 Report — Wave W3.3 Firdar Activations

## Summary

Closed remaining P1/P2 findings: exact activation-rules load test, missing-key tests for firdar_major/firdar_minor, canon validation, module contract accuracy, and FirdarContext contract placement.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/firdar.py` | Added `_validate_firdar_canon()`; fixed module contract; moved `FirdarContext.__init__` contract |
| `apps/solarsage/tests/test_firdar.py` | 40 tests (up from 35): exact load test, missing-key tests, canon validation tests |

## Fixes

### P1: Exact activation-rules load test
Sends a single focused request with only `["firdar_major", "firdar_minor"]` and asserts `load_count == 1`. No second request.

### P1: Missing firdar_major/firdar_minor KeyError tests
Added `test_strength_missing_firdar_major_key` and `test_strength_missing_firdar_minor_key`. Each removes the respective key from a copy of the rules and asserts `KeyError`.

### P1: Module contract + canon validation
- Removed inaccurate "unknown sign/strength keys" wording from invariants
- Added `_validate_firdar_canon()` with checks for: `cycle_years > 0`, `minor_divisions > 0`, non-empty sequences, valid lord/years entries, sequence sum == cycle_years, `node_minor_sequence` length == `minor_divisions`
- Tests: `minor_divisions = 0` → ValueError, sequence sum mismatch → ValueError, node sequence length mismatch → ValueError

### P2: FirdarContext.__init__ contract placement
Moved `START_FUNCTION_CONTRACT` to directly above `def __init__`, added `returns: None`.

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar firdar + others | 66 passed, 1 warning |
| Sidecar full | 92 passed, 1 warning |
| API targeted | 23 passed |
| API full | 690 passed, 5 skipped, 1 warning |
| Hashseed × 3 | Identical |
| Artifact (117 activations) | wave=W3.3, major=SUN/0.65, minor=SATURN/0.40, age=45.68767123 |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`cf3c2df`

## Push Status

`NOT_ATTEMPTED`
