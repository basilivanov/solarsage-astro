# W5 Rework 01 TZ — Complete Runtime Integration and Versioned Cache

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 implementation/report
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/02_arch_review.md
```

Do not redo unrelated frontend or semantic W6 work. This is backend W5 completion.

## Required Work

### 1. Wire versioned cache key into DB persistence

Files likely touched:

```text
apps/api/app/db/models.py
apps/api/alembic/versions/<new>_today_payload_cache_v2_key.py
apps/api/app/services/today_service.py
apps/api/app/services/calendar_service.py
apps/api/app/services/cache_key_service.py
apps/api/tests/test_today_cache_v2_key.py
apps/api/tests/test_alembic_roundtrip.py
```

Implement the `00_TZ.md` cache requirement fully:

- Add `TodayPayloadCache` columns:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`
- Add an Alembic migration after `0018`.
- Use `op.batch_alter_table(...)` for constraint changes so SQLite round-trip remains green.
- Replace old uniqueness with:

```text
(user_id, target_date, profile_hash, cache_key_hash)
```

- Keep downgrade working.
- Keep old rows safe: old/missing/wrong cache metadata must miss. If migration needs `server_default`, use defaults that do not accidentally validate as current unless all fields match.

Update `TodayService`:

- Build the cache key from:
  - user_id
  - target_date
  - profile_hash
  - calculation_version
  - activation_layer_version
  - selected scoring version
  - canon versions hash
  - prompt version
  - frontend payload version
- Use the key in `_get_cached_payload()` and `_cache_payload()`.
- Store all version columns on write.
- Do not rely only on JSON `content_version`.

Semantic cache:

- Store the same cache/version metadata inside `SemanticLayerCache.semantic_json`.
- `CalendarService` may use semantic cache only if all relevant version/cache fields match current expectations.
- Version mismatch must cause a miss and recompute.

### 2. Integrate CalendarService with runtime scorer

Files likely touched:

```text
apps/api/app/services/calendar_service.py
apps/api/tests/test_calendar_v2_dual_run.py
apps/api/tests/test_calendar_endpoints.py
```

Required behavior:

- `_compute_and_cache_day_status()` must:
  - normalize day;
  - filter day-scored signals;
  - build an activation layer;
  - call `DayScoringRuntimeService.compute(...)`;
  - use `dual.selected_result["day_status"]`.
- Default `SOLARSAGE_V2_DUAL_RUN=true`, `SOLARSAGE_V2_ENABLED=false`:
  - V2 is computed;
  - selected calendar status remains V1.
- `SOLARSAGE_V2_ENABLED=true`:
  - selected calendar status uses V2.
- Calendar payload cache and semantic cache reads must validate the same version identity as `/day`.

Required tests must instantiate/use `CalendarService`, not only `DayScoringRuntimeService`.

### 3. Wire sidecar `/v1/activation-layer` into API runtime V2

Files likely touched:

```text
apps/api/app/clients/solarsage_client.py
apps/api/app/services/today_service.py
apps/api/app/services/calendar_service.py
apps/api/tests/test_today_service_v2_dual_run.py
apps/api/tests/test_calendar_v2_dual_run.py
apps/api/tests/test_today_meta_versions.py
```

Required behavior:

- Add `SolarSageClient.get_activation_layer(...)` for sidecar `/v1/activation-layer`.
- Validate the sidecar response using existing API `ActivationLayer` schema, or a small response schema if needed.
- Call sidecar activation-layer only when V2 may be computed:
  - `SOLARSAGE_V2_DUAL_RUN=true`, or
  - `SOLARSAGE_V2_ENABLED=true`.
- Use the returned sidecar layer in:

```python
ActivationLayerService().build(..., sidecar_activation_layer=sidecar_layer)
```

- When `SOLARSAGE_V2_ENABLED=false`, sidecar activation-layer failure must fail open to V1:
  - no user-visible `/day` failure;
  - visible `dual.v2_error`/structured log metadata.
- When `SOLARSAGE_V2_ENABLED=true`, sidecar activation-layer failure must fail loudly.

Important: do not use port `8001` as API. Use the existing `SolarSageClient` base URL, which points to canonical sidecar `18091`.

Required tests:

- In `/day` dual-run, mock sidecar activation-layer response and assert it is passed to `ActivationLayerService` / `ScoringV2Service`.
- Include at least one non-W2 technique, e.g. `annual_profection` or `firdar_major`, to prove W3 techniques can reach V2 scoring.
- Test fail-open behavior in dual-run and fail-loud behavior in enabled mode.

### 4. Remove duplicate V1 scoring in TodayService

Remove the dead direct call:

```python
ScoringService().score_day(day_signals)
```

from the fresh `/day` path before `DayScoringRuntimeService`. Runtime service owns V1/V2 selection.

### 5. Improve tests so they catch current broken state

Minimum required additions/updates:

- DB model/migration tests prove new columns exist.
- Cache write/read test proves:
  - selected V1 and selected V2 produce different cache rows or at least different `cache_key_hash`;
  - stale old row does not satisfy current lookup;
  - canon/prompt/frontend/scoring version mismatch misses.
- CalendarService test proves actual calendar status selection changes under `SOLARSAGE_V2_ENABLED=true`.
- Semantic cache mismatch test proves stale semantic status cannot win.
- Runtime sidecar activation-layer test includes non-W2 technique.
- Logging registry test still passes for `scoring.v2_diff`.

## Required Verification

Run without piping through `tail` unless `set -o pipefail` is set first. Report exact commands/results.

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_runtime_flags.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_service_v2_dual_run.py \
  tests/test_calendar_v2_dual_run.py \
  tests/test_today_meta_versions.py \
  tests/test_day_endpoints.py \
  tests/test_calendar_endpoints.py \
  tests/test_alembic_roundtrip.py \
  tests/test_log_envelope_shape.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_basil_2026_07_08_v2_golden.py -q
```

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

```bash
python3 scripts/check_logging_guardrails.py
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/04_rework_01_report.md
```

Include:

- changed files;
- migration ID;
- exact DB cache columns/unique constraint;
- proof that `/day` and `CalendarService` both use `DayScoringRuntimeService`;
- proof that sidecar activation-layer reaches V2 scoring;
- exact verification command outputs;
- final git status;
- commit SHA;
- `Push: NOT_ATTEMPTED`.

Commit implementation, migration, tests, and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W5 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
