# W5 Rework 02 Architect Review

Status: REWORK REQUIRED

Reviewed implementation commit: `b7c6fe4`
Report commit: `681b77d`
Reviewed against: `06_rework_02_TZ.md`

## Findings

### P0 — Calendar still trusts `TodayPayloadCache` without versioned cache identity

Evidence:
- `apps/api/app/services/calendar_service.py:208-224` queries `TodayPayloadCache` only by `user_id`, `target_date`, and `profile_hash`.
- It does not build the current cache key, does not filter by `cache_key_hash`, and does not validate `scoring_version`, `calculation_version`, `activation_layer_version`, `canon_versions_hash`, `llm_prompt_version`, or `frontend_payload_version`.

Impact:
- In V2-enabled mode, calendar can return a stale V1 payload status for the same user/date/profile.
- This violates the W5 requirement that cache reads use versioned identity and that profile/content alone is not enough.

Required fix:
- In `_get_cached_day_status()`, build the current cache key using `selected_scoring_version_for_flags()` and the prepared profile hash before reading `TodayPayloadCache`.
- Query or validate `TodayPayloadCache` by the same version identity used for `/day`, including `cache_key_hash`.
- Add a regression where same user/date/profile has two payload cache rows with different hashes and calendar returns/misses only the matching one.

### P0 — Calendar semantic cache validation is incomplete

Evidence:
- `apps/api/app/services/calendar_service.py:226-245` validates only `content_version`, `profile_hash`, and `scoring_version`.
- The TZ explicitly requires validation of the full semantic cache identity: `cache_key_hash`, `calculation_version`, `activation_layer_version`, `scoring_version`, `canon_versions_hash`, `llm_prompt_version`, and `frontend_payload_version`.
- The report also states only `scoring_version` is validated for Calendar.

Impact:
- Old semantic cache rows with the same scoring version but different canon, activation layer, prompt, frontend payload, or cache hash can still override current scoring semantics.

Required fix:
- Build the expected current cache key in Calendar and require every identity field to match before trusting `SemanticLayerCache`.
- Missing legacy identity fields must miss and recompute; do not default missing `scoring_version` to `"1"` as a passing identity.
- Add tests for wrong `cache_key_hash` and at least one other wrong identity field causing recompute.

### P0 — Calendar V2-enabled sidecar failure is swallowed

Evidence:
- `apps/api/app/services/calendar_service.py:300-302` re-raises sidecar activation-layer failure when `settings.solarsage_v2_enabled` is true.
- `apps/api/app/services/calendar_service.py:376-378` immediately catches every `Exception`, rolls back, and returns `None`.

Impact:
- The required fail-loud behavior for `SOLARSAGE_V2_ENABLED=true` is not actually visible to callers; Calendar silently drops status instead.

Required fix:
- Preserve shadow fail-open only when V2 is not selected.
- When V2 is enabled and sidecar activation-layer fails, let the error propagate or convert it to an explicit service error consistent with the API layer.
- Add a Calendar test proving enabled mode does not return `None` on sidecar failure.

### P1 — Sidecar activation-layer requests omit `current_location`

Evidence:
- `apps/api/app/services/today_service.py:242-252` and `apps/api/app/services/calendar_service.py:289-299` pass birth data and target data but never pass current location.
- `06_rework_02_TZ.md` requires `current_location` from `current_lat/current_lon/current_tz` when available.

Impact:
- V2 activation inputs are incomplete for users whose current location differs from birth location.

Required fix:
- Pass current location when profile has current coordinates/timezone. If the client method signature lacks it, extend the client method and tests.
- Add a test asserting current location is included when available and omitted when incomplete.

### P1 — Shadow sidecar fail-open is not visible

Evidence:
- `apps/api/app/services/today_service.py:238-256` stores `sidecar_error` but never logs it or exposes metadata.
- Calendar catches sidecar failure in shadow mode and proceeds without a log/metadata marker.
- The TZ requires visible metadata/logging so shadow V2 failure is not silent.

Impact:
- A broken sidecar activation-layer can be hidden in dual-run mode, defeating W5 observability.

Required fix:
- Emit a structured log event for shadow fail-open in TodayService and CalendarService, with user/date and error class/message.
- If there is an existing V2 meta/debug field, populate it; otherwise logging is the minimum acceptable visible evidence for W5.
- Add tests or log guard assertions proving the fail-open path emits the marker.

### P1 — Rework tests do not prove the required integration

Evidence:
- `apps/api/tests/test_today_meta_versions.py:295-329` only awaits `mock_client.get_activation_layer()` directly. It never instantiates `TodayService`, never patches `get_solarsage_client`, never verifies `ActivationLayerService.build()`, and never proves runtime V2 receives a non-W2 technique.
- `apps/api/tests/test_today_service_v2_dual_run.py` and `apps/api/tests/test_calendar_v2_dual_run.py` exercise only `DayScoringRuntimeService`, not TodayService or CalendarService integration.
- `apps/api/tests/test_today_cache_v2_key.py` only tests pure hash construction; it does not insert two cache rows or prove SQL lookup/upsert uses `cache_key_hash`.

Impact:
- The required W5 behavior can regress while these tests remain green.

Required fix:
- Replace false-positive tests with service-level async tests that exercise actual TodayService and CalendarService paths.
- Cover:
  - `/day` dual-run fetches sidecar layer and passes an `annual_profection` activation into V2 scoring;
  - Calendar computed status path fetches sidecar layer;
  - V1-only mode does not call sidecar;
  - shadow fail-open and enabled fail-loud;
  - duplicate same user/date/profile cache rows with different hashes;
  - stale payload and semantic rows with wrong identity miss.

## Notes

- `TodayService._get_cached_payload()` and `_cache_payload()` now include `cache_key_hash` when `cache_key` is passed. That part is directionally correct.
- `TodayService` rebuilds the write key from `dual.selected_scoring_version`. Calendar should do the same or assert helper/runtime agreement before storing semantic identity.
