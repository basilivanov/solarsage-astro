# Rework 01 Report — Wave W3.2 Profection Activations

## Summary

Fixed P0 monthly profection drift, P1 debug/audit metadata gaps, P1 unknown sign fallback, and P2 timezone boundary test requirement.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/activation_builder.py` | Fixed monthly drift (non-drifting anniversaries), added `house_cusp_longitude` to 4 profection debugs, `_ruler_of_sign` raises `ValueError` for unknown signs |
| `apps/solarsage/tests/test_profections.py` | Added drift parametric test (4 cases), `house_cusp_longitude` assertions, `test_unknown_sign_raises`, `test_timezone_boundary_local_date` |
| `scripts/audit_sidecar_activation.py` | Audit metadata: wave=W3.2 when profections requested, includes techniques list |
| `artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json` | Regenerated with fix: house_cusp_longitude in debug, wave=W3.2 |

## Fixes

### P0: Monthly profection drift
Replaced chained clamp (`probe = next_probe`) with non-drifting anniversary counting from `annual_year_start`:
```python
for step in range(1, 13):
    anniversary = _add_months_with_clamp(annual_year_start, step)
    if anniversary <= target_local:
        completed_month_steps = step
```

Tested boundary cases:
- `2026-03-29` => steps=4, house=2 (before step 5 anniversary at Mar 30)
- `2026-03-30` => steps=5, house=3 (exact step 5 anniversary)
- `2026-07-29` => steps=8, house=6 (before step 9 anniversary at Jul 30)
- `2026-07-30` => steps=9, house=7 (exact step 9 anniversary)

### P1: Debug house_cusp_longitude added
All 4 profection activations now include:
```json
"house_cusp_longitude": 0.0,   // annual house 10 (Aries)
"house_cusp_longitude": 240.0   // monthly house 6 (Sagittarius)
```

### P1: Audit metadata fixed
- `wave` is `W3.2` when profection techniques are requested
- `techniques` lists the exact requested technique list

### P1: Unknown sign raises ValueError
`_ruler_of_sign("NotASign")` now raises `ValueError("Unknown sign: ...")` instead of silently returning `SATURN`.

### P2: Timezone boundary test
Added `test_timezone_boundary_local_date` proving that target `date` is treated as local date independently of timezone. Same local date across `Pacific/Kiritimati` and `America/Anchorage` produces identical profection results.

## Verification Results

| Gate | Result |
|------|--------|
| `pytest test_profections test_activation_layer_endpoint test_activation_transits test_activation_schema -q` (sidecar) | 31 passed, 1 warning |
| `pytest tests/ -q` (sidecar full) | 52 passed, 1 warning |
| `pytest test_activation_layer_profections test_activation_layer_transits test_activation_layer_contract test_today_meta_versions -q` (API) | 19 passed |
| `pytest tests/ -q` (API full) | 686 passed, 5 skipped, 1 warning |
| Regenerated artifact | house_cusp_longitude present, wave=W3.2 |
| `PYTHONHASHSEED=random` × 3 | All identical ✓ |
| `house_cusp_longitude` in debug | All 4 profection activations ✓ |
| Unsupported W3+ in artifact | None ✓ |
| `sidecar_activation_layer=None` | Still None ✓ |
| `git diff --check` (whitespace) | clean ✓ |

## Commit

`305c3ad`

## Push Status

`NOT_ATTEMPTED`
