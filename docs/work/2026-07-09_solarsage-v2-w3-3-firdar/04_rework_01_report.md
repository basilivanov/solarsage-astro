# Rework 01 Report — Wave W3.3 Firdar Activations

## Summary

Fixed P0 decimal age denominator, P1 strength fallbacks, P1 GRACE contracts, P1 Feb 29 support, P2 context caching, P2 node period coverage, P2 historical fixture verification.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/firdar.py` | Fixed age denominator (birthday interval); Feb 29 clamp; GRACE contracts; display names |
| `apps/solarsage/solarsage/services/activation_builder.py` | Firdar context caching; strict strength lookup; updated header; node display names |
| `apps/solarsage/tests/test_firdar.py` | 32 tests (up from 14): decimal age, Feb 29, node periods, spy, historical fixtures |

## Fixes

### P0: Decimal age denominator
Replaced `days_in_birth_year` (calendar year) with actual birthday interval:
```
last_birthday = birthday_on_or_before(target)
next_birthday = next_birthday_after(last_birthday)
age_years = completed_years + elapsed_days / (next_birthday - last_birthday)
```
Regression: `birth 1990-07-01 target 2000-06-30` → age `9.997...` < 10.0, major SUN. Boundary: exact birthday → age 10.0, VENUS.

### P1: Feb 29 births
`_clamp_birthday` uses Feb 28 in non-leap years. `_completed_years` compares against clamped birthday. Tests cover non-leap before clamp, exact clamp, leap year exact, and one-year anniversary.

### P1: Strict strength lookup
Replaced `period_base.get("firdar_major", 0.65)` with `_get_period_strength(rules, "firdar_major")` which raises KeyError on missing keys. Test confirms `_get_period_strength` raises for nonexistent techniques.

### P2: Firdar context computed once
`firdar_ctx` tuple cached before the technique loop; calculated on first encounter, reused on second. Spy test proves `calculate_firdar` is called exactly once.

### P1: GRACE contracts
firdar.py: complete `START_MODULE_CONTRACT`, `END_MODULE_CONTRACT`, `START_MODULE_MAP`, function contracts for all public/non-trivial functions, semantic blocks.

### P2: Node period coverage
Tests: age 70 → NORTH_NODE_TRUE major, SATURN minor; age 73 → SOUTH_NODE major, SATURN minor. Evidence uses `North Node`/`South Node`, not raw keys. by_planet refs validated.

### P2: Historical fixtures
Loaded `vasiliy_2026-05-30.json` and `test_user_2026-06-15.json`. Verified: is_day_birth flags, canon sequence match (first 7 periods), first-period subperiod rotation, active period lords.

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar targeted | 63 passed, 1 warning |
| Sidecar full | 84 passed, 1 warning |
| API targeted | 23 passed |
| API full | 690 passed, 5 skipped, 1 warning |
| Decimal age regression | age < 10 (9.997) → SUN; age = 10.0 → VENUS |
| Feb 29: non-leap clamped | age = 1.0 on Feb 28 |
| Feb 29: leap exact | age = 4.0 on Feb 29 |
| Spy: calculate_firdar called once | ✓ |
| Strength: missing key raises | KeyError ✓ |
| Hashseed × 3 | Identical |
| sidecar_activation_layer=None | Still None |
| Whitespace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
