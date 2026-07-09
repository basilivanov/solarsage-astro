# W5 Rework 03 Architect Review

Status: REWORK REQUIRED

Reviewed implementation commit: `1e95b95`
Report commit: `451101f`
Reviewed against: `09_rework_03_TZ.md`

## Findings

### P0 — Cache identity still does not include the actual activation-layer version

Evidence:
- `apps/api/app/services/today_service.py:184-189` builds the cache-read key with only `scoring_version`.
- `apps/api/app/services/today_service.py:300-306` rebuilds the write key with only `scoring_version`.
- `apps/api/app/services/calendar_service.py:212-217` and `:345-350` do the same.
- `apps/api/app/services/cache_key_service.py:52-54` defaults `activation_layer_version=None`.
- Therefore `TodayPayloadCache.activation_layer_version` and semantic `activation_layer_version` are written as `None`, even though `activation_layer.activation_layer_version` is `"al-1.0"` in the actual payload.

Impact:
- Changing activation-layer contract/version will not invalidate `/day` or Calendar status caches.
- The W5 versioned cache identity is only partially real; one of its required fields is present in the DB/JSON shape but not semantically active.

Required fix:
- Build read keys with the current expected activation-layer version, not `None`.
- After `ActivationLayerService.build()`, rebuild the write key from actual runtime facts:
  - `calculation_version=activation_layer.calculation_version`
  - `activation_layer_version=activation_layer.activation_layer_version`
  - `scoring_version=dual.selected_scoring_version`
- Store these values in `TodayPayloadCache` and `SemanticLayerCache`.
- Add tests proving `activation_layer_version` changes the cache hash and stale `None` rows miss.

### P0 — Calendar semantic validation still omits `activation_layer_version`

Evidence:
- `apps/api/app/services/calendar_service.py:250-259` validates `cache_key_hash`, `calculation_version`, `scoring_version`, `canon_versions_hash`, `llm_prompt_version`, and `frontend_payload_version`.
- It does not validate `activation_layer_version`.
- The report claims all identity fields are validated, but the code does not match that claim.

Impact:
- Semantic cache rows with the wrong activation-layer version can still be trusted if the hash is also currently computed without that version.

Required fix:
- Include `activation_layer_version` in Calendar semantic identity validation.
- Add a regression where semantic cache differs only by `activation_layer_version`; it must miss.

### P0 — Required real integration tests are still missing

Evidence:
- `apps/api/tests/test_today_meta_versions.py:295-329` is unchanged and still only awaits `mock_client.get_activation_layer()` directly. It never exercises `TodayService`.
- `apps/api/tests/test_today_service_v2_dual_run.py` and `apps/api/tests/test_calendar_v2_dual_run.py` still exercise only `DayScoringRuntimeService`, not TodayService or CalendarService integration.
- `apps/api/tests/test_today_cache_v2_key.py` still tests pure hash construction only. It does not insert two rows, check SQL predicates, or prove stale rows miss.
- Rework 03 changed only `test_calendar_endpoints.py`; it did not satisfy the W5 service-level test requirements.

Impact:
- The exact regression from Rework 01/02 can return and tests will still pass.

Required fix:
- Replace false-positive tests with service-level async tests that fail if TodayService/CalendarService stop calling sidecar activation-layer or stop passing it into V2 scoring.
- Add cache tests that exercise DB rows and service lookup/upsert behavior, not only pure hash construction.

### P1 — `current_location` is sent with incomplete current-location data

Evidence:
- `apps/api/app/services/today_service.py:240-247` and `apps/api/app/services/calendar_service.py:300-308` send `current_location` when `current_lat` and `current_lon` exist, even if `current_tz` is missing. They fill `tz` with `target_tz`, which can be the birth timezone.
- `09_rework_03_TZ.md` requires passing current location only when complete and omitting it when incomplete.

Impact:
- The sidecar can receive a current location with coordinates from one place and timezone from birth/default fallback.

Required fix:
- Require `current_lat`, `current_lon`, and `current_tz` to be present before passing `current_location`.
- Add tests for complete and incomplete current location.

### P1 — TodayService logs a shadow fallback even in V2-enabled fail-loud mode

Evidence:
- `apps/api/app/services/today_service.py:262-278` logs `"V2 shadow mode: ... using local fallback"` before checking `settings.solarsage_v2_enabled`.
- If V2 is enabled, the method then raises.

Impact:
- Logs can falsely claim shadow fallback happened for a request that actually failed loudly.

Required fix:
- Check `settings.solarsage_v2_enabled` before emitting shadow fallback logs.
- In enabled mode, either raise without fallback log or emit a distinct failure log that does not claim local fallback was used.

### P1 — Verification evidence is still too weak

Evidence:
- The tmux run used `pytest ... 2>&1 | tail -5` without `set -o pipefail`, despite the TZ forbidding that.
- The full API suite output shown in tmux was `1 failed, 735 passed, 5 skipped`, while the report summarizes it as `735 passed, 5 skipped (1 pre-existing oracle failure)`.

Impact:
- Acceptance cannot rely on the reported gates.

Required fix:
- Run required commands again without `tail`, or with `set -o pipefail` and a preserved exit code.
- If a known oracle failure remains, report it as a failed gate with exact test name and reason; do not call the full suite green.

## Notes

- Calendar now queries `TodayPayloadCache` by `cache_key_hash`, which is the right shape once the key actually includes all required version fields.
- Calendar now has the right direction for fail-loud, but tests must prove the exact sidecar failure behavior rather than relying on broad exception behavior.

