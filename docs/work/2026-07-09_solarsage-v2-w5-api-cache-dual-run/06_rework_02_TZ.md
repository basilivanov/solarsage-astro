# W5 Rework 02 TZ — Wire Sidecar Layer and Fix Versioned Cache Queries

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 01
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/05_rework_01_review.md
```

This rework is narrow. Do not change frontend, W6 semantic payload shape, or scoring constants.

## Required Work

### 1. Actually wire sidecar activation layer into runtime V2

Current broken state:

- `SolarSageClient.get_activation_layer()` exists.
- `/day` and calendar still pass `sidecar_activation_layer=None`.

Required behavior:

- Add a small helper in an appropriate service/module:

```python
def should_compute_v2() -> bool:
    return settings.solarsage_v2_enabled or settings.solarsage_v2_dual_run
```

- In `TodayService`, when `should_compute_v2()` is true:
  - call `client.get_activation_layer(...)`;
  - build request from `UserProfile` and target:
    - `birth_date=profile.birthday.isoformat()`
    - `birth_time=profile.birth_time.strftime("%H:%M")`
    - `birth_lat=float(profile.birth_lat)`
    - `birth_lon=float(profile.birth_lon)`
    - `birth_tz=profile.birth_tz`
    - `target_date=target_date.isoformat()`
    - `target_time="12:00"`
    - `target_tz=profile.current_tz or profile.birth_tz or "UTC"`
    - `house_system=natal_context_dict.get("house_system", "PLACIDUS")`
    - `current_location` from `current_lat/current_lon/current_tz` when available, else omit.
  - pass the returned layer into:

```python
ActivationLayerService().build(..., sidecar_activation_layer=sidecar_layer)
```

- In `CalendarService._compute_and_cache_day_status()`, do the same when V2 may be computed.

Failure policy:

- If sidecar activation-layer fails and `SOLARSAGE_V2_ENABLED=false`, fail open:
  - use local fallback activation layer;
  - V1 selected output must still return;
  - include visible metadata/logging so the V2 shadow failure is not silent.
- If sidecar activation-layer fails and `SOLARSAGE_V2_ENABLED=true`, raise/fail loudly.

Test requirements:

- Replace `test_today_service_not_wired_to_sidecar_activation_layer` with inverse coverage.
- Test `/day` dual-run calls `get_activation_layer()` and passes a sidecar activation containing at least one non-W2 technique, e.g. `annual_profection`, into V2 scoring.
- Test calendar computed status path calls `get_activation_layer()` when V2 may be computed.
- Test V1-only mode does not call `get_activation_layer()`.
- Test shadow fail-open and enabled fail-loud behavior.

### 2. Fix versioned cache queries and writes

Current broken state:

- read/write selects only `(user_id, target_date, profile_hash)` and then checks/mutates `cache_key_hash`.
- selected scoring version is unknown when the cache key is built, so V2-enabled can use a V1 cache key.

Required behavior:

- Add/select a helper for the selected scoring version implied by flags:

```python
def selected_scoring_version_for_flags() -> int | str:
    return "ss-scoring-2.0" if settings.solarsage_v2_enabled else 1
```

- Build the cache-read key with this selected scoring version before DB lookup.
- After fresh scoring, assert `dual.selected_scoring_version == selected_scoring_version_for_flags()` or rebuild the write key with `dual.selected_scoring_version`.
- In `_get_cached_payload()` query by:

```python
user_id
target_date
profile_hash
cache_key_hash
```

- In `_cache_payload()` query/upsert by the same four fields.
- Never mutate an existing row with a different `cache_key_hash`.

Test requirements:

- Insert two `TodayPayloadCache` rows for same user/date/profile with different hashes. Prove lookup returns the matching row.
- Prove no `MultipleResultsFound` happens.
- Prove V2-enabled writes `scoring_version="ss-scoring-2.0"` and a different `cache_key_hash` from V1.
- Prove old row with empty `cache_key_hash` misses.

### 3. Version semantic cache identity

Required behavior:

- Store these fields in `SemanticLayerCache.semantic_json` for `/day` and calendar:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`
- `CalendarService._get_cached_day_status()` must validate them before trusting semantic status.
- A profile/content match alone is not enough.

Test requirements:

- Semantic cache with matching content/profile but wrong `scoring_version` or `cache_key_hash` must miss and recompute.

### 4. Keep migration/model shape

The `0019` migration may stay if valid. Ensure:

- `apps/api/app/db/models.py` and migration agree.
- Alembic round-trip passes.
- If you change migration after it was committed locally, it is acceptable because it has not been pushed/deployed.

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
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/07_rework_02_report.md
```

Include:

- changed files;
- exact proof that `/day` and calendar call sidecar activation-layer when V2 may be computed;
- exact proof that V1-only mode does not call sidecar activation-layer;
- exact proof that cache lookup/upsert uses `cache_key_hash` in SQL predicates;
- semantic cache version metadata fields;
- exact verification outputs;
- final git status;
- commit SHA;
- `Push: NOT_ATTEMPTED`.

Commit implementation and report. Do not push/deploy.

## Callback

After implementation, verification, report, and commit:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W5 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
