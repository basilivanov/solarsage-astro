# W5 Rework 01 Architect Review

Status: REWORK REQUIRED
Reviewed commits: `abffe00..ffd3b93`

## Findings

### P0 — Sidecar activation layer is still not wired into runtime V2

Evidence:

- `SolarSageClient.get_activation_layer()` was added, but `TodayService` still calls:

```python
sidecar_activation_layer=None
```

at `apps/api/app/services/today_service.py:246-255`.

- `CalendarService` also still calls:

```python
sidecar_activation_layer=None
```

at `apps/api/app/services/calendar_service.py:276-285`.

- `apps/api/tests/test_today_meta_versions.py:295-317` still contains the old guard asserting `TodayService` must not wire a non-None sidecar activation layer.

Impact:

- Runtime V2 still uses only the local W2 fallback activation layer, not W3 profections/firdar/returns/progressions/eclipse.
- The main reason for W5 dual-run is not achieved: shadow diffs do not exercise the actual SolarSage V2 activation layer.
- The report says sidecar activation-layer is “wired in /day and calendar”, but the code contradicts that.

Required fix:

- Add a helper for deciding whether V2 will be computed.
- When V2 may be computed (`SOLARSAGE_V2_DUAL_RUN` or `SOLARSAGE_V2_ENABLED`), call `client.get_activation_layer(...)`.
- Pass the returned layer to `ActivationLayerService().build(..., sidecar_activation_layer=sidecar_layer)`.
- Remove/replace the old “not wired” guard test with inverse tests proving non-W2 sidecar technique data reaches V2.
- In shadow mode, sidecar activation-layer failures must fail open to V1 with visible metadata/log; in V2-enabled mode they must fail loudly.

### P0 — Versioned cache lookup/upsert still queries by the old non-versioned key

Evidence:

- `TodayService._get_cached_payload()` selects only `user_id`, `target_date`, `profile_hash` at `apps/api/app/services/today_service.py:578-585`, then checks `cache_key_hash` after fetching a single row.
- `TodayService._cache_payload()` also selects only `user_id`, `target_date`, `profile_hash` at `apps/api/app/services/today_service.py:617-624`.
- The new DB uniqueness permits multiple rows for the same `(user_id, target_date, profile_hash)` with different `cache_key_hash`.

Impact:

- Once V1 and V2, or two canon/prompt/frontend versions, exist for the same day/profile, `scalar_one_or_none()` can raise `MultipleResultsFound`.
- Upsert can update the wrong cache row instead of inserting a new versioned row.
- The DB unique constraint exists, but the app code does not use it as the lookup key.

Required fix:

- Include `TodayPayloadCache.cache_key_hash == cache_key.cache_key_hash` directly in read and write queries.
- Do not fetch a non-versioned row and then compare hash.
- On write, upsert only the exact versioned row.
- Add a regression that creates two rows for the same user/date/profile with different hashes and proves each lookup returns the matching row, not an exception or arbitrary row.

### P0 — Cache key for `/day` is built before selected scoring version is known and defaults to V1

Evidence:

- `/day` builds `cache_key = build_today_cache_key(...)` at `apps/api/app/services/today_service.py:178-183` without passing scoring version, so it defaults to `1`.
- Later the selected scoring version is determined at `apps/api/app/services/today_service.py:257-266`.
- `_cache_payload()` stores the original cache key, not a key rebuilt with `dual.selected_scoring_version`.

Impact:

- When `SOLARSAGE_V2_ENABLED=true`, a V2-selected payload can be stored under a V1 cache key.
- Cache invalidation by scoring version is still incorrect.

Required fix:

- Determine the selected scoring version from flags before cache read:
  - V2 enabled -> `"ss-scoring-2.0"`;
  - otherwise -> `1`.
- Build the read cache key with that selected scoring version.
- After fresh computation, assert/rebuild using `dual.selected_scoring_version` and use that key for write.
- Add a test proving V2-enabled fresh payload writes `scoring_version="ss-scoring-2.0"` and a different `cache_key_hash` from V1.

### P1 — Calendar semantic cache is still only content/profile-versioned

Evidence:

- `CalendarService._get_cached_day_status()` still accepts semantic cache when `content_version` and `profile_hash` match at `apps/api/app/services/calendar_service.py:225-243`.
- `_compute_and_cache_day_status()` still stores only `profile_hash`, `content_version`, and `semantic_layer` at `apps/api/app/services/calendar_service.py:306-310`.

Impact:

- A semantic status generated with V1 can survive when selected scoring changes to V2 if `TODAY_CONTENT_VERSION` is unchanged.
- Canon/prompt/frontend/scoring version mismatches are not rejected.

Required fix:

- Store and validate the same version identity fields used by the today cache:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`
- Add a stale semantic cache test where matching content/profile but different scoring/cache hash must miss.

### P1 — Tests still do not prove sidecar activation-layer runtime wiring

Evidence:

- Existing sidecar activation-layer tests prove `ActivationLayerService` accepts sidecar dicts, but not that `TodayService` or `CalendarService` fetch/pass them.
- The old guard test still asserts non-wiring.

Impact:

- The current broken state can pass tests.

Required fix:

- Add `/day` and calendar tests that mock `SolarSageClient.get_activation_layer()` returning an activation with a non-W2 technique, e.g. `annual_profection`.
- Assert `ScoringV2Service`/runtime receives an activation layer containing that activation when dual-run or V2-enabled is active.
- Assert `get_activation_layer()` is not called in V1-only mode.

## Verification Note

I did not run the full suite because static code evidence shows multiple P0 requirements are still unmet. Execute `06_rework_02_TZ.md`.
