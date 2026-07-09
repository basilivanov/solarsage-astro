# Agent Report — Wave W3.4 Returns (Rework 03)

## Summary

Test-contract closure: malformed current_location endpoint tests, no-TodayService-wiring regression test.

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Added 4 tests: valid current_location returns 200; missing lat/lon/empty returns 422 |
| `apps/api/tests/test_today_meta_versions.py` | Added `test_today_service_not_wired_to_sidecar_activation_layer` — source-invariant guard |
| `docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md` | Updated |

## Added Tests

### Malformed current_location tests
- `test_current_location_valid_returns_200` — valid lat/lon/tz returns 200
- `test_current_location_missing_lat_returns_422` — missing lat returns 422
- `test_current_location_missing_lon_returns_422` — missing lon returns 422
- `test_current_location_empty_dict_returns_422` — empty dict returns 422

### No-TodayService-wiring guard
- `test_today_service_not_wired_to_sidecar_activation_layer` — reads `today_service.py`, asserts `sidecar_activation_layer=None` exists and no non-None assignment exists

## Verification Results

| Gate | Result |
|------|--------|
| Sidecar endpoint + return tests | 34 passed, 1 warning |
| API returns + today meta | 12 passed |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
