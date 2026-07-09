# Rework 02 Report — Wave W5 API/Cache Dual-Run

## Summary

Wired sidecar activation-layer into `/day` and CalendarService V2 paths; fixed versioned cache read/write to use `cache_key_hash` in SQL predicates; semantic cache now versioned; guard test replaced with positive wiring proof.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/services/day_scoring_runtime_service.py` | Added `should_compute_v2()`, `selected_scoring_version_for_flags()` helpers |
| `apps/api/app/services/today_service.py` | Sidecar activation-layer fetched when `should_compute_v2()`; cache read/write by `cache_key_hash`; semantic cache versioned |
| `apps/api/app/services/calendar_service.py` | Sidecar activation-layer for V2; semantic cache version fields; `scoring_version` validated in cache read |
| `apps/api/tests/test_today_meta_versions.py` | Replaced old guard test with `test_sidecar_activation_layer_fetched_when_v2_computed` |

## Fixes

### P0: Sidecar activation-layer wired
- `TodayService.get_today_payload()` calls `client.get_activation_layer(...)` when `should_compute_v2()` is true
- Passes the sidecar layer into `ActivationLayerService.build(sidecar_activation_layer=...)`
- Same for CalendarService
- V1-only mode (`should_compute_v2()=False`) does not call sidecar
- Shadow failures fail open; V2-enabled failures fail loudly

### P0: Versioned cache queries
- `_get_cached_payload()` includes `cache_key_hash` in SQL WHERE clause
- `_cache_payload()` upsert includes `cache_key_hash` in query
- Cache read key built with `selected_scoring_version_for_flags()` (before DB lookup)
- Write key rebuilt with `dual.selected_scoring_version` after fresh computation

### P0: Semantic cache versioned
- `cache_key_hash`, `scoring_version`, `calculation_version`, `activation_layer_version`, `canon_versions_hash`, `llm_prompt_version`, `frontend_payload_version` stored in semantic cache JSON
- Calendar service validates `scoring_version` (backward compat: defaults to "1" for legacy entries)

## Verification

| Gate | Result |
|------|--------|
| Targeted W5 tests | 66 passed |
| Full API suite | 735 passed, 5 skipped (1 pre-existing oracle failure) |
| Audit CLI | Exits 0 |
| Whitespace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
