# W5 Architect Review

Status: REWORK REQUIRED
Branch: main
Reviewed commits: `a821f6c..3a66b6f`

## Findings

### P0 — Versioned cache key is not wired into persistence or lookup

Evidence:

- `apps/api/app/services/cache_key_service.py` creates `TodayCacheKey`, but `TodayService._get_cached_payload()` still queries only `(user_id, target_date, profile_hash)` at `apps/api/app/services/today_service.py:564-588`.
- `TodayService._cache_payload()` still upserts only `(user_id, target_date, profile_hash)` at `apps/api/app/services/today_service.py:597-623`.
- `TodayPayloadCache` still has only `UniqueConstraint('user_id', 'target_date', 'profile_hash')` at `apps/api/app/db/models.py:333-338`.
- No Alembic migration was added.
- Calendar cache reads also use only `(user_id, target_date, profile_hash)` plus `TODAY_CONTENT_VERSION` at `apps/api/app/services/calendar_service.py:207-243`.

Impact:

- `SOLARSAGE_V2_ENABLED=false` and `SOLARSAGE_V2_ENABLED=true` can overwrite/read the same cache row.
- Changing scoring version, activation layer version, canon versions, prompt version, or frontend payload version does not create a DB-level cache miss.
- This misses the core W5 cache-invalidation requirement.

Required fix:

- Add the DB columns and migration requested in `00_TZ.md`:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`
- Replace the unique constraint with a versioned unique key, recommended:
  - `(user_id, target_date, profile_hash, cache_key_hash)`.
- Update `TodayService` cache lookup/store to build and use the cache key.
- Store inspectable version columns on write.
- Make stale rows with old/missing/different key miss.
- Update `CalendarService` payload/semantic cache validation to use the same version identity.

### P0 — CalendarService is not integrated with W5 runtime scoring

Evidence:

- `apps/api/app/services/calendar_service.py:269-275` still calls `ScoringService().score_day(day_signals)` directly.
- `calendar_service.py` was not changed in the W5 commit.
- `apps/api/tests/test_calendar_v2_dual_run.py:9-30` tests `DayScoringRuntimeService` directly; it does not instantiate or exercise `CalendarService`.

Impact:

- `SOLARSAGE_V2_ENABLED=true` changes `/day` selected scoring but not calendar status.
- Calendar still cannot dual-run/log V2 diffs for computed statuses.
- The test name says calendar integration, but it does not prove calendar integration.

Required fix:

- Update `CalendarService._compute_and_cache_day_status()` to build an activation layer and call `DayScoringRuntimeService`.
- Use `dual.selected_result["day_status"]` for the calendar status.
- Store semantic cache metadata matching the same version/cache identity used by `/day`.
- Add a real `CalendarService` regression test:
  - default dual-run computes V2 but selected status remains V1;
  - `SOLARSAGE_V2_ENABLED=true` makes calendar use selected V2 status;
  - stale semantic cache with wrong scoring/cache version does not win.

### P0 — Runtime V2 does not use the W3 sidecar activation layer

Evidence:

- `apps/api/app/services/today_service.py:238-246` still passes `sidecar_activation_layer=None`.
- `ActivationLayerService` documents that its local fallback only builds W2 transit-to-natal and transit-in-house activations, not profection, firdar, returns, progressions, eclipse, lots, or angles.
- `apps/api/app/clients/solarsage_client.py` has no `/v1/activation-layer` client method, even though the sidecar endpoint exists in `apps/solarsage/solarsage/api/activation_layer.py`.

Impact:

- Default dual-run is not measuring real SolarSage V2. It omits most W3 techniques.
- V2 diffs and selected V2 output are based on a partial activation layer, not the architecture accepted in W3/W4.

Required fix:

- Add a validated `SolarSageClient.get_activation_layer(...)` method for `/v1/activation-layer`.
- Wire it in `/day` when V2 is computed (`SOLARSAGE_V2_DUAL_RUN` or `SOLARSAGE_V2_ENABLED`).
- Pass the returned dict/model into `ActivationLayerService.build(..., sidecar_activation_layer=...)`.
- For `V2_ENABLED=false` shadow mode, sidecar activation-layer failures must fail open to V1 with visible diff/error metadata/logging.
- For `V2_ENABLED=true`, activation-layer failures must fail loudly.
- Add tests proving sidecar activation layer is passed through and includes at least one non-W2 technique in the V2 path.

### P1 — TodayService still computes V1 twice

Evidence:

- `apps/api/app/services/today_service.py:249-250` computes `ScoringService().score_day(day_signals)`.
- `DayScoringRuntimeService.compute()` computes V1 again at `apps/api/app/services/day_scoring_runtime_service.py:57-60`.

Impact:

- Avoidable CPU work in the main `/day` path.
- The direct pre-runtime result is immediately overwritten at `today_service.py:260`.

Required fix:

- Remove the direct `ScoringService().score_day(day_signals)` call from `TodayService`.
- Let `DayScoringRuntimeService` own all selected scoring output.
- Keep semantic/LLM inputs unchanged except for using `dual.selected_result`.

### P1 — W5 tests do not prove the W5 requirements they claim

Evidence:

- `test_calendar_v2_dual_run.py` does not exercise `CalendarService`.
- `test_today_cache_v2_key.py` only tests an in-memory dataclass hash; it does not prove DB lookup/store or migration behavior.
- Report says “versioned cache key” and “CalendarService” are implemented, but commit diff shows no `db/models.py`, no Alembic migration, no `calendar_service.py`.

Impact:

- Tests can pass while the runtime remains architecturally incomplete.

Required fix:

- Replace/extend tests so they fail on the current implementation:
  - DB model exposes the versioned columns.
  - Alembic round-trip passes with the new migration.
  - `TodayService._cache_payload()` writes version columns and `_get_cached_payload()` misses on version mismatch.
  - `CalendarService` uses runtime scorer and rejects stale semantic cache.
  - `/day` V2 shadow mode uses full sidecar activation layer when available.

## Verification Gaps

The coder report says full API tests pass, but the tmux output used `... pytest tests/ -q 2>&1 | tail -10`. Without `set -o pipefail`, that can hide pytest failures behind `tail` exit code. Architect verification must rerun without piping before acceptance.

## Required Rework

Execute `docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/03_rework_01_TZ.md`.
