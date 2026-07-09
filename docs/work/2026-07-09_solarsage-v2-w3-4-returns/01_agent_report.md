# Agent Report — Wave W3.4 Returns (Rework 01)

## Summary

Fixed P0 location and P0 lunar-latest blockers. Return charts now actually use `current_location`; lunar return selects latest valid crossing; `house_system` is no longer silently ignored.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/utils/ephemeris.py` | `calculate_houses_cusps` now accepts `house_system` param; supports PLACIDUS/WHOLE_SIGN; unknown systems raise `ValueError` |
| `apps/solarsage/solarsage/services/returns.py` | Added `return_lat`/`return_lon`/`return_tz` params; return charts use location for houses; lunar: latest-JD selection |
| `apps/solarsage/solarsage/services/activation_builder.py` | Passes `ret_lat`/`ret_lon`/`ret_tz` to return calculations; natal chart uses requested house_system |
| `apps/solarsage/tests/test_solar_return.py` | 11 tests (up from 9): relocation changes IDs, no fallback with current_location, strength strictness |
| `apps/solarsage/tests/test_lunar_return.py` | 11 tests (up from 9): latest-crossing regression, relocation changes IDs |
| `apps/api/tests/test_activation_layer_returns.py` | All debug fields required in fixture, preserved through validation |
| `artifacts/audit/2026-07-08/20_sidecar_activation_layer_w3_4_returns.json` | Regenerated (artifact clean) |

## Fixes

### P0: current_location drives return houses
`calculate_solar_return` and `calculate_lunar_return` now accept `return_lat`/`return_lon`/`return_tz`. Return chart houses/ASC/MC are built at the return location, not birth location. Relocating to equator produces different activation IDs and resolves house system as PLACIDUS.

### P0: Lunar return selects latest valid crossing
Replaced residual-based selection with latest-JD selection. Collects all candidate crossings in the search window, keeps `candidate_jd <= target_jd` with `residual <= 0.001°`, selects `max(candidate_jd)`. Test proves `2026-07-16` target returns `2461236.95` (latest), not `2461209.52` (previous).

### P1: house_system forwarded
`calculate_houses_cusps(jd, lat, lon, house_system)` now accepts a requested house system. Unknown systems raise `ValueError`. High-latitude override (PLACIDUS→WHOLE_SIGN at lat≥60) preserved.

### P1: Strength strictness tests
Added `test_strength_missing_solar_return_key` and `test_strength_missing_lunar_return_key` — both prove `KeyError`.

## Relocation probe (architect verification)

```python
fallback warnings count = 1 ✓
relocated warnings = [] ✓
relocated location_source = current_location ✓
relocated resolved_house_system = PLACIDUS (equator) ✓
fallback ids != relocated ids ✓
```

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar targeted (all waves) | 95 passed, 1 warning |
| API targeted | 28 passed |
| W3.4 artifact | 133 activations, wave=W3.4 |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`b5c8bcd`

## Push Status

`NOT_ATTEMPTED`
