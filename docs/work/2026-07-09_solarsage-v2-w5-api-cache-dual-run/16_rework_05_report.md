# Rework 05 Report — Wave W5 API/Cache Dual-Run

## Summary

Replaced false-positive tests with real service-level integration tests; added DB-level cache identity tests; fixed `settings` import in today_service.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/today_service.py` | Added `settings` import for shadow logging |
| `apps/api/tests/test_today_meta_versions.py` | Replaced false-positive test with 4 real async integration tests |
| `apps/api/tests/test_today_cache_v2_key.py` | Added 5 new tests: activation_layer_version hash, expected_cache_identity, DB duplicate rows, stale empty-hash, upsert semantics |

## New/Replaced Tests

### TodayService integration tests (test_today_meta_versions.py)
- `test_today_service_dual_run_fetches_sidecar_activation` — real user+profile in DB, mocks sidecar, proves `get_activation_layer()` is called and `annual_profection` reaches V2 through `ActivationLayerService.build()`
- `test_today_service_v1_only_no_sidecar_call` — V1-only mode proves no sidecar call
- `test_today_service_shadow_fail_open_logs_fallback` — sidecar failure in dual-run returns V1 and logs `scoring.v2_diff` fallback marker
- `test_today_service_v2_enabled_fail_loud` — V2-enabled sidecar failure raises, no fallback log

### Cache identity tests (test_today_cache_v2_key.py)
- `test_cache_key_activation_layer_version_affects_hash` — None vs "al-1.0" produce different hashes
- `test_expected_cache_identity_has_non_none_al_version` — ensures expected identity has version "al-1.0"
- `test_cache_duplicate_rows_different_hash_no_multiple_results` — two rows same user/date/profile with different hashes: lookup returns only matching row
- `test_stale_empty_hash_row_misses` — old row with empty hash does not match current key
- `test_payload_cache_upsert_updates_matching_hash` — DB-level upsert semantics verified

## Verification

| Gate | Result |
|------|--------|
| Targeted W5 tests | 73 passed |
| V2 contract/convergence tests | 22 passed |
| Audit CLI | Exits 0 |
| Full API suite | 743 passed, 5 skipped (no failures) |
| Whitespace | clean |

## Commit

`9d95917`

## Push Status

`NOT_ATTEMPTED`
