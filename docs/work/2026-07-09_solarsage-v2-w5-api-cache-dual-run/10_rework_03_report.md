# Rework 03 Report — Wave W5 API/Cache Dual-Run

## Summary

Fixed Calendar payload cache versioned identity, full semantic cache validation, Calendar V2-enabled fail-loud, current_location passing, shadow fail-open logging, and updated tests.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/calendar_service.py` | Payload cache queries by `cache_key_hash`; semantic cache validates ALL 8 identity fields; V2-enabled fail-loud propagates; shadow fail-open logged; current_location passed |
| `apps/api/app/services/today_service.py` | current_location passed to sidecar; shadow fail-open structured log |
| `apps/api/tests/test_calendar_endpoints.py` | Calendar structure test includes identity fields in semantic cache; content version test includes `cache_key_hash` |

## Fixes

### P0: Calendar payload cache versioned identity
- `_get_cached_day_status()` now builds cache key and queries by `cache_key_hash` + all version fields
- Same user/date/profile with different hashes → different rows, only matching one returned

### P0: Calendar semantic cache full identity
- Validates all 8 identity fields: `cache_key_hash`, `calculation_version`, `activation_layer_version`, `scoring_version`, `canon_versions_hash`, `llm_prompt_version`, `frontend_payload_version`
- Missing legacy fields → miss (no default fallback)

### P0: V2-enabled fail-loud
- `_compute_and_cache_day_status()` outer except re-raises when `settings.solarsage_v2_enabled` is true
- Shadow mode (V2 disabled) silently returns V1 with structured log

### P1: current_location passed
- `TodayService` and `CalendarService` build current_location dict from `profile.current_lat/lon/tz` when complete

### P1: Shadow fail-open logged
- `scoring.v2_diff` event with level=warning, error message, and `fallback: "local_activation"`

## Verification

| Gate | Result |
|------|--------|
| Targeted W5 tests | 66 passed |
| Full API suite | 735 passed, 5 skipped (1 pre-existing oracle failure) |
| Audit CLI | Exits 0 |
| Whitespace | clean |

## Commit

`1e95b95`

## Push Status

`NOT_ATTEMPTED`
