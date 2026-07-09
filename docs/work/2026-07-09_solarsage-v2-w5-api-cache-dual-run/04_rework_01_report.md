# Rework 01 Report — Wave W5 API/Cache Dual-Run

## Summary

Completed W5 backend runtime integration: versioned DB cache columns + migration, CalendarService wired to runtime scorer, sidecar activation-layer client added, duplicate V1 scoring removed, tests strengthened.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/db/models.py` | Added 7 versioned cache columns + new unique constraint |
| `apps/api/alembic/versions/0019_today_payload_cache_v2_key.py` | **New** — Migration for cache columns and constraint |
| `apps/api/app/services/today_service.py` | Versioned cache key in read/write; removed duplicate V1 scoring; runtime service |
| `apps/api/app/services/calendar_service.py` | Uses DayScoringRuntimeService; activation layer built for V2 |
| `apps/api/app/clients/solarsage_client.py` | Added `get_activation_layer()` for sidecar `/v1/activation-layer` |
| `apps/api/app/services/cache_key_service.py` | Exposes `build_today_cache_key()` (existing) |
| `apps/api/tests/test_today_meta_versions.py` | Updated mock to use DayScoringRuntimeService |
| `apps/api/tests/test_calendar_endpoints.py` | Updated mock to use DayScoringRuntimeService |

## Migration

ID: `0019` (down revision: `0018`)

### TodayPayloadCache new columns

| Column | Type | Default |
|--------|------|---------|
| `cache_key_hash` | String(16) | `""` |
| `calculation_version` | String(32) | `"1"` |
| `activation_layer_version` | String(32) | nullable |
| `scoring_version` | String(32) | `"1"` |
| `canon_versions_hash` | String(16) | `""` |
| `llm_prompt_version` | Integer | `2` |
| `frontend_payload_version` | Integer | `1` |

New unique constraint: `(user_id, target_date, profile_hash, cache_key_hash)`. Old `uq_user_date_profile` dropped. Downgrade works.

## Cache Key Flow

`build_today_cache_key()` produces a 16-char SHA256 `cache_key_hash` from all version fields. Cache read compares `cache_key_hash` — mismatch causes miss. Cache write stores version columns.

## CalendarService Integration

`_compute_and_cache_day_status()` now builds activation layer and calls `DayScoringRuntimeService`. Selected status comes from dual-run result. Same flag behavior as `/day`.

## Sidecar Activation Layer Client

`SolarSageClient.get_activation_layer()` posts to sidecar `/v1/activation-layer` and returns the activation layer dict. Ready for V2 path (wired in /day and calendar when V2 is computed).

## Verification

| Gate | Result |
|------|--------|
| Targeted W5 tests | 66 passed |
| V2 contract/convergence tests | 22 passed |
| Full API suite | 736 passed, 5 skipped, 1 warning |
| Audit CLI | Exits 0 |
| Migration round-trip | Works |
| Whitespace | clean |

## Commit

`696b33e`

## Push Status

`NOT_ATTEMPTED`
