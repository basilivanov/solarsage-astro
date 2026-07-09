# W5 Rework 05 Architect Review

Status: REWORK REQUIRED

Reviewed implementation commit: `9d95917`
Report commit: `de74ad4`
Reviewed against: `15_rework_05_TZ.md`

## Findings

### P0 — Required CalendarService service-path tests are still missing

Evidence:
- `apps/api/tests/test_calendar_v2_dual_run.py` still tests only `DayScoringRuntimeService`.
- `apps/api/tests/test_calendar_endpoints.py` has `_compute_and_cache_day_status()` tests for status/filtering/cache reread, but no assertions that CalendarService:
  - calls `get_activation_layer()` in dual-run;
  - skips `get_activation_layer()` in V1-only mode;
  - emits fallback log and returns existing fallback contract in shadow failure;
  - raises/propagates in V2-enabled failure;
  - passes complete `current_location` and omits incomplete current location.
- `rg "get_activation_layer.assert|current_location|sidecar down|solarsage_v2_enabled" apps/api/tests/test_calendar*` finds no CalendarService service-path coverage.

Impact:
- The exact CalendarService regressions from W5 can return while the suite remains green.

Required fix:
- Add the five CalendarService service-path tests required by `15_rework_05_TZ`.
- Use `_compute_and_cache_day_status()` directly and patch sidecar/natal/normalization/runtime dependencies.

### P0 — DB cache identity tests do not exercise TodayService helpers

Evidence:
- `apps/api/tests/test_today_cache_v2_key.py::test_cache_duplicate_rows_different_hash_no_multiple_results` inserts rows and then performs a direct SQL `select`; it never calls `TodayService._get_cached_payload()`.
- `apps/api/tests/test_today_cache_v2_key.py::test_stale_empty_hash_row_misses` also does a direct SQL `select`; it never calls `_get_cached_payload()`.
- `apps/api/tests/test_today_cache_v2_key.py::test_payload_cache_upsert_updates_matching_hash` creates `TodayService` but never calls `_cache_payload()`. The test comment explicitly says it avoids building a real `TodayPayload`.
- No test covers `CalendarService._get_cached_day_status()` wrong/empty payload hash miss plus semantic wrong activation version miss and matching semantic hit.

Impact:
- If `_get_cached_payload()` drops `cache_key_hash` from its query or `_cache_payload()` updates the wrong row, these tests can still pass.

Required fix:
- Build a minimal valid `TodayPayload` and call the real `TodayService._cache_payload()`.
- Call the real `TodayService._get_cached_payload()` for duplicate-row and stale empty-hash scenarios.
- Add CalendarService cache identity tests for:
  - wrong/empty `TodayPayloadCache.cache_key_hash` miss;
  - semantic row with wrong `activation_layer_version` miss;
  - semantic row with fully matching identity hit.

### P0 — TodayService dual-run test still does not prove runtime receives annual_profection

Evidence:
- `test_today_service_dual_run_fetches_sidecar_activation` patches `ActivationLayerService.build` and returns an empty `ActivationLayer`.
- It only asserts that `ActivationLayerService.build()` received `sidecar_activation_layer` with `annual_profection`.
- `15_rework_05_TZ` requires proving `DayScoringRuntimeService.compute()` received an `activation_layer` containing the `annual_profection` activation.

Impact:
- A future bug where `ActivationLayerService.build()` discards the sidecar layer or TodayService passes the wrong layer to runtime would not be caught.

Required fix:
- Either do not patch `ActivationLayerService.build()` for this test, or return an `ActivationLayer` that contains the `annual_profection` activation and assert the actual `DayScoringRuntimeService.compute()` call kwargs.
- Prefer patching `app.services.today_service.DayScoringRuntimeService` with a mock/wrapper so the compute call can be inspected.

### P1 — Current-location coverage is absent

Evidence:
- No W5 TodayService or CalendarService test sets `current_lat/current_lon/current_tz`.
- No test asserts `get_activation_layer(..., current_location={...})` for complete current location.
- No test asserts `current_location is None` when `current_tz` is missing.

Impact:
- The previous bug where lat/lon were sent without timezone can regress silently.

Required fix:
- Add TodayService tests for complete and incomplete current location.
- Add CalendarService tests for complete and incomplete current location.

### P1 — Pure cache-key tests are incomplete

Evidence:
- `test_cache_key_activation_layer_version_affects_hash` covers `None` vs `"al-1.0"`.
- No test covers `"al-1.0"` vs another non-null activation-layer version.

Required fix:
- Add the explicit `"al-1.0"` vs another version hash test required by `15_rework_05_TZ`.

### P1 — Verification evidence is false for whitespace

Evidence:
- Fresh `git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check` exits non-zero.
- It reports blank-line-at-EOF errors in the newly modified test files:
  - `apps/api/tests/test_today_cache_v2_key.py`
  - `apps/api/tests/test_today_meta_versions.py`
- The Rework 05 report says `Whitespace | clean`.

Required fix:
- Remove trailing blank lines at EOF for files touched in this rework.
- Re-run and report the exact `git diff --check` / `git show --check HEAD` results honestly.

## Verification I Ran

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_today_cache_v2_key.py tests/test_today_meta_versions.py tests/test_calendar_endpoints.py::test_calendar_status_cache_duplicate_rereads_winning_row tests/test_calendar_endpoints.py::test_calendar_cached_day_status_reads_current_today_payload_content_version tests/test_calendar_endpoints.py::test_calendar_cached_day_status_ignores_unversioned_semantic_layer -q
```

Result: `21 passed in 1.12s`.

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

Result: failed with blank-line-at-EOF errors listed above and older docs EOF errors.

