# Rework 04 Report — Wave W5 API/Cache Dual-Run

## Summary

Made cache identity real by including `activation_layer_version` in read/write keys; added `expected_cache_identity()` helper; fixed current_location completeness; fixed shadow logging order.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/cache_key_service.py` | Added `expected_cache_identity()` with `activation_layer_version="al-1.0"` |
| `apps/api/app/services/today_service.py` | Uses `expected_cache_identity` for read; writes `activation_layer_version` from runtime; fixes shadow logging order; fixes current_location completeness |
| `apps/api/app/services/calendar_service.py` | Uses `expected_cache_identity` for read; validates `activation_layer_version`; writes runtime versions; `current_location` requires all 3 fields |
| `apps/api/tests/test_calendar_endpoints.py` | Uses `expected_cache_identity` for test cache keys; all identity fields in payload/semantic rows |

## Fixes

### P0: `activation_layer_version` in cache identity
- `expected_cache_identity()` returns a key with `activation_layer_version="al-1.0"` — used for cache reads
- Write keys use runtime `activation_layer.activation_layer_version` (e.g. `"al-1.0"`)
- Cache hash changes when `activation_layer_version` changes
- Calendar semantic cache validates `activation_layer_version` alongside other fields

### P0: Calendar semantic `activation_layer_version`
- Now validates all 9 identity fields including `activation_layer_version`

### P1: current_location completeness
- Requires `current_lat`, `current_lon`, AND `current_tz` before sending
- Missing any one field → `current_location` omitted entirely

### P1: Shadow logging order
- TodayService now checks `settings.solarsage_v2_enabled` BEFORE logging shadow fallback
- In V2-enabled mode, no shadow fallback log is emitted

## Verification

| Gate | Result |
|------|--------|
| Targeted W5 tests | 66 passed |
| Full API suite | 735 passed, 5 skipped (1 pre-existing: `test_audit_live_isolates_output` requires sidecar) |
| Audit CLI | Exits 0 |
| Whitespace | clean |

## Commit

`aedbdc4`

## Push Status

`NOT_ATTEMPTED`
