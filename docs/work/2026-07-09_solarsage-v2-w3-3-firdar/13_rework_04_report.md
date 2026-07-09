# Rework 04 Report — Wave W3.3 Firdar Activations

## Summary

Closed final P1/P2 findings: caller-supplied canon validation, contract cleanup, FirdarContext contract placement, unused import removal.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/firdar.py` | Added `_validate_firdar_canon()` call in `calculate_firdar()` for caller-supplied canon; fixed `calculate_firdar` contract (removed strength keys); moved `FirdarContext.__init__` contract above method; removed unused `import math` |
| `apps/solarsage/tests/test_firdar.py` | 41 tests (up from 40): all 4 canon validation tests call `calculate_firdar(canon=bad)` directly; removed `_validate_canon_test` helper; added night sequence sum mismatch test |

## Fixes

### P1: calculate_firdar(canon=bad) now raises ValueError
`calculate_firdar()` now calls `_validate_firdar_canon(canon)` when a non-None canon is provided. All four malformed-canon scenarios raise `ValueError` through the public API:

- `minor_divisions = 0` → `ValueError` (not `ZeroDivisionError`)
- day sequence sum mismatch → `ValueError`
- night sequence sum mismatch → `ValueError`
- node minor sequence length mismatch → `ValueError`

### P1: calculate_firdar contract fixed
Removed `KeyError on missing canon keys or strength keys`. Now documents:
- `KeyError` on missing required canon keys
- `ValueError` on malformed canon values
- No mention of strength keys (belongs to activation_builder, not firdar)

### P2: FirdarContext.__init__ contract moved
Contract now sits above `def __init__`, not inside the argument list. `returns: None` preserved.

### P3: Unused imports removed
- `import math` removed from `_validate_firdar_canon()`
- `_validate_canon_test` helper removed from test file

### Grep proof
`rg 'strength keys|unknown sign|import math|load_count <=' firdar.py test_firdar.py` → no matches

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar firdar + others | 72 passed, 1 warning |
| Sidecar full | 93 passed, 1 warning |
| API targeted | 23 passed |
| API full | 690 passed, 5 skipped, 1 warning |
| Hashseed × 3 | Identical |
| Artifact (117 activations) | unchanged |
| sidecar_activation_layer=None | Still None |
| `rg` unwanted patterns | No matches |
| Whitespace | clean |

## Commit

`f27d394`

## Push Status

`NOT_ATTEMPTED`
