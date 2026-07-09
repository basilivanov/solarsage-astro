# Rework 02 Report — Wave W3.3 Firdar Activations

## Summary

Closed remaining fixture/GRACE/test-discipline findings. Core period calculation unchanged.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/activation_builder.py` | Activation rules loaded once (not twice); updated firdar section |
| `apps/solarsage/solarsage/services/firdar.py` | Added function contracts for 7 non-trivial functions; corrected module contract |
| `apps/solarsage/tests/test_firdar.py` | 35 tests (up from 32): full fixture period comparison, node endpoint assertions, activation-rules load spy |

## Fixes

### P1: Activation rules loaded once
`_load_activation_rules()` called once and cached for both firdar_major and firdar_minor strength lookups. Spy test confirms single load per request.

### P1: GRACE function contracts completed
Added `START_FUNCTION_CONTRACT` / `END_FUNCTION_CONTRACT` for:
- `_display_name`
- `_clamp_birthday`
- `_completed_years`
- `_last_birthday`
- `_next_birthday`
- `_age_years_decimal`
- `FirdarContext.__init__`

Module contract corrected: removed unrelated unknown-sign wording, documents actual canon/date/division failures.

### P1: Full fixture period comparison
`_compare_fixture_periods()` compares all 9 periods against canon sequence:
- lords, years, start_age, end_age with numeric tolerance
- all 7 subperiod rotations
- node-period minor sequence
- total years == cycle_years

Both Vasiliy (night) and test_user (day) fixtures verified.

### Legacy integer-age limitation documented
test_user fixture `current_sub_period = MARS` was computed with integer age 36 by legacy collector. W3.3 date-precise calculation gives minor=SUN (age 36.4137). The fixture's own period table confirms SUN subperiod at the correct age range. The new test explicitly documents this distinction and verifies from the period table, not the legacy `current_sub_period` field.

### P2: Strong node endpoint assertions
Exact tests for NORTH_NODE_TRUE and SOUTH_NODE at ages 70.0/73.0:
- stable ids (`firdar_major__PERIOD_LORD__NORTH_NODE_TRUE`)
- readable evidence (`North Node is major firdar lord`)
- target_key and target_planet correctness
- by_planet refs

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar firdar + others | 63 passed, 1 warning |
| Sidecar full | 87 passed, 1 warning |
| API targeted | 23 passed |
| API full | 690 passed, 5 skipped, 1 warning |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`11574e6`

## Push Status

`NOT_ATTEMPTED`
