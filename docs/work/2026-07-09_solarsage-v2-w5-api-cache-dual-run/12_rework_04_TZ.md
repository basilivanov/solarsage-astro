# W5 Rework 04 TZ — Make Cache Identity Real and Add Actual Integration Tests

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 03
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/11_rework_03_review.md
```

This is still W5 only. Do not change frontend, W6 UI payloads, scoring constants, or unrelated interpretation behavior.

## Required Work

### 1. Make `activation_layer_version` part of the real cache key

Current bug: cache rows and semantic JSON have an `activation_layer_version` field, but service-built keys currently leave it as `None`.

Required behavior:

- Define one small helper for the current expected cache identity used before cache read. It must include:
  - `calculation_version`
  - `activation_layer_version`
  - `selected_scoring_version_for_flags()`
  - canon versions hash via `build_today_cache_key()`
  - prompt/frontend versions
- Use the current expected activation-layer version from the contract/default, e.g. `"al-1.0"` derived from `ActivationLayer` schema/default or a single explicit constant. Do not duplicate magic strings in multiple services.
- TodayService and CalendarService cache-read keys must use this helper.
- After fresh computation, rebuild the write key from actual runtime facts:
  - `calculation_version=activation_layer.calculation_version`
  - `activation_layer_version=activation_layer.activation_layer_version`
  - `scoring_version=dual.selected_scoring_version`
- Store write-key values in `TodayPayloadCache` and semantic cache JSON.
- If expected read identity and actual write identity diverge, log it clearly and use the actual write key for storage.

Add tests:

- `activation_layer_version` changes `cache_key_hash`.
- A payload/semantic row with `activation_layer_version=None` misses.
- A row with wrong `activation_layer_version` misses.
- A row with matching `activation_layer_version` hits.

### 2. Finish Calendar semantic identity validation

In `CalendarService._get_cached_day_status()`:

- Validate `activation_layer_version` along with all other identity fields:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`
- Missing legacy identity fields must miss.

Add a regression where semantic cache differs only by `activation_layer_version`; it must miss and recompute.

### 3. Replace false-positive tests with real service-level tests

Remove or rewrite tests that prove only direct mock behavior.

Required service-level coverage:

- TodayService dual-run:
  - creates a real test user/profile/context;
  - patches `get_solarsage_client`;
  - sidecar `get_activation_layer()` returns a layer containing non-W2 technique `annual_profection`;
  - proves the service path calls `get_activation_layer()`;
  - proves the activation layer passed to V2/runtime includes `annual_profection`.
- Calendar computed status path:
  - creates a real test user/profile/context;
  - V2 may be computed;
  - proves Calendar calls `get_activation_layer()`.
- V1-only mode:
  - proves no sidecar activation-layer call.
- Shadow fail-open:
  - sidecar activation-layer failure returns V1-selected output/status;
  - structured log marker is emitted.
- V2-enabled fail-loud:
  - sidecar activation-layer failure raises/propagates; it must not return `None`.
- Cache DB behavior:
  - duplicate same user/date/profile rows with different hashes do not raise `MultipleResultsFound`;
  - lookup/upsert uses current `cache_key_hash`;
  - stale empty-hash or wrong-version rows miss.

Tests must exercise TodayService/CalendarService or the DB helpers directly. Tests that only call `DayScoringRuntimeService` or `mock_client.get_activation_layer()` directly do not satisfy this requirement.

### 4. Fix `current_location` completeness

For TodayService and CalendarService:

- Pass `current_location` only when `current_lat`, `current_lon`, and `current_tz` are all present.
- Omit `current_location` entirely when any of those fields is missing.
- Do not fill current location timezone from birth timezone or target fallback.

Add tests:

- Complete current location is passed.
- Missing `current_tz` omits `current_location`.

### 5. Fix shadow logging order

For TodayService and CalendarService:

- In `SOLARSAGE_V2_ENABLED=true`, do not log `"shadow mode"` or `"using local fallback"` for activation-layer failure.
- In shadow mode, log the fallback marker exactly once.
- Use distinct messages for fail-loud versus shadow fail-open if both are logged.

### 6. Verification discipline

Run required commands without `tail`, unless `set -o pipefail` is set and exit status is preserved.

If a known external/oracle test still fails, report:

- exact command;
- exact failed test name;
- why it is external/pre-existing;
- whether it blocks W5 acceptance.

Do not summarize a failed full suite as green.

## Required Verification

Run and report exact commands/results:

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
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/13_rework_04_report.md
```

Include:

- changed files;
- exact proof that `activation_layer_version` is part of cache key read/write identity;
- exact proof that Calendar semantic cache validates `activation_layer_version`;
- exact proof that false-positive tests were replaced by real service-level tests;
- exact proof for current-location complete/incomplete behavior;
- exact proof for shadow fail-open and V2-enabled fail-loud;
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
  -d '{"prompt":"Wave W5 Rework 04 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/13_rework_04_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/11_rework_03_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/12_rework_04_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
