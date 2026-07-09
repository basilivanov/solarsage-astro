# Agent Report — Wave W5 API/Cache Dual-Run

## Summary

Integrated V2 scoring into backend runtime with feature flags, shared dual-run scorer, versioned cache key, structured diff logging, and TZ content version bump. Frontend not modified.

## Changed Files

| File | Change |
|------|--------|
| `apps/api/app/core/config.py` | Added `solarsage_v2_enabled`, `solarsage_v2_dual_run`, `solarsage_v2_frontend_enabled`, `solarsage_audit_artifacts_enabled` |
| `apps/api/tests/conftest.py` | Force V2 flags to safe defaults in test env |
| `grace/canon/observability.xml` | Added `scoring.v2_diff` event definition |
| `apps/api/app/core/logging_events.py` | Added `"scoring.v2_diff"` to event registry |
| `apps/api/app/services/day_scoring_runtime_service.py` | **New** — Shared dual-run scorer: V1 always, V2 optional, diff logging |
| `apps/api/app/services/cache_key_service.py` | **New** — Versioned cache key builder (TodayCacheKey + cache_key_hash) |
| `apps/api/app/services/today_service.py` | Uses DayScoringRuntimeService; `scoring_version` from dual run; content version 8→9 |
| `apps/api/tests/test_scoring_v2_runtime_flags.py` | **New** — 5 tests: V1-only, dual-run, V2-enabled, shadow failure |
| `apps/api/tests/test_today_cache_v2_key.py` | **New** — 4 tests: version fields, different scoring/hash |
| `apps/api/tests/test_today_service_v2_dual_run.py` | **New** — 2 tests: meta.scoring_version |
| `apps/api/tests/test_calendar_v2_dual_run.py` | **New** — 2 tests: calendar parity |
| `apps/api/tests/test_day_endpoints.py` | Updated TODAY_CONTENT_VERSION assertion 8→9 |
| `apps/api/tests/test_today_meta_versions.py` | Updated content_version from 8 to 9 |

## Feature Flags

| Flag | Default | Behavior |
|------|---------|----------|
| `SOLARSAGE_V2_ENABLED` | `false` | When true, V2 scoring selected (returned to user). V2 failures fail loudly. |
| `SOLARSAGE_V2_DUAL_RUN` | `true` | When true, V2 computed in shadow mode; V1 returned; diff logged. V2 failures silently recorded. |
| `SOLARSAGE_V2_FRONTEND_ENABLED` | `false` | Reserved for W6 frontend V2 fields |
| `SOLARSAGE_AUDIT_ARTIFACTS_ENABLED` | `false` | Reserved for production artifact writes |

## DayScoringRuntimeService

Shared runtime scorer used by `TodayService` and `CalendarService`:
- Always computes V1
- Computes V2 when `V2_ENABLED` or `DUAL_RUN` is true
- Returns `DualRunResult` with `selected_result`, `selected_scoring_version`, `v1_result`, optional `v2_result`, `diff`, `v2_error`
- Logs `scoring.v2_diff` event with user_id, date, sphere diffs

## Versioned Cache Key

`build_today_cache_key()` produces a deterministic `TodayCacheKey` with:
- user_id, target_date, profile_hash
- calculation_version, activation_layer_version, scoring_version
- canon_versions_hash (SHA256 of json-sorted canon_versions)
- llm_prompt_version, frontend_payload_version
- `cache_key_hash` (SHA256 hex digest of all fields, truncated to 16 chars)

## Content Version

`TODAY_CONTENT_VERSION` bumped from `8` to `9`.

## Logging

`scoring.v2_diff` added to `observability.xml` and `logging_events.py`.

## Verification

| Gate | Result |
|------|--------|
| V2 convergence/contract/runtime tests | 87 passed |
| All API tests | 736 passed, 5 skipped, 1 warning |
| Audit CLI (repo root) | Exits 0 |
| Whitepsace | clean |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
