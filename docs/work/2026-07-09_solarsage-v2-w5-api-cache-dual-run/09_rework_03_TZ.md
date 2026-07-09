# W5 Rework 03 TZ — Finish Versioned Calendar Cache and Real Integration Tests

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 02
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/08_rework_02_review.md
```

This rework is still W5 only. Do not change frontend, W6 semantic payload UI, scoring constants, or unrelated day interpretation behavior.

## Required Work

### 1. Calendar payload cache must use versioned identity

In `CalendarService._get_cached_day_status()`:

- Build the expected current cache key from:
  - `user_id`
  - `target_date`
  - prepared `profile_hash`
  - `selected_scoring_version_for_flags()`
- Do not trust a `TodayPayloadCache` row selected only by `(user_id, target_date, profile_hash)`.
- Query by `cache_key_hash` or validate all stored version columns before returning status.
- Required identity fields:
  - `cache_key_hash`
  - `calculation_version`
  - `activation_layer_version`
  - `scoring_version`
  - `canon_versions_hash`
  - `llm_prompt_version`
  - `frontend_payload_version`

Add/adjust tests:

- Same user/date/profile has two `TodayPayloadCache` rows with different hashes; Calendar must return only the matching current row.
- A stale V1 row must not satisfy Calendar when V2 is selected.
- Old row with empty `cache_key_hash` must miss.

### 2. Calendar semantic cache must validate the full identity

In `CalendarService._get_cached_day_status()`:

- Validate all semantic identity fields listed above, not only `scoring_version`.
- Missing legacy identity fields must miss and recompute.
- Do not default absent `scoring_version` to `"1"` as a passing identity.

Add/adjust tests:

- Matching content/profile but wrong `cache_key_hash` misses.
- Matching content/profile but wrong `canon_versions_hash` or `activation_layer_version` misses.
- Missing identity fields from a legacy semantic row miss.

### 3. Calendar V2-enabled sidecar failure must fail loudly

Current bug: an inner `raise` is swallowed by the outer broad `except`.

Required behavior:

- If `settings.solarsage_v2_enabled` is true and `get_activation_layer()` fails, Calendar must not silently return `None`.
- Preserve shadow fail-open only when V2 is not selected.
- Keep rollback behavior for real DB/integrity failures, but do not hide V2-enabled activation-layer failure.

Add tests:

- Calendar dual-run/shadow sidecar failure returns V1 status and records visible log/metadata.
- Calendar V2-enabled sidecar failure raises or propagates explicit service failure instead of returning `None`.

### 4. Pass current location to sidecar activation-layer

For TodayService and CalendarService:

- When profile has complete current location fields, pass them to `SolarSageClient.get_activation_layer()`.
- Use:
  - `current_lat`
  - `current_lon`
  - `current_tz`
- If any required current-location field is missing, omit current location entirely rather than sending partial data.
- If client signature/schema needs extending, update it in the same rework.

Add tests:

- Current location is passed when complete.
- Current location is omitted when incomplete.

### 5. Make shadow fail-open observable

For TodayService and CalendarService:

- In shadow mode (`SOLARSAGE_V2_ENABLED=false`, dual-run true), sidecar activation-layer failure may fail open.
- That fail-open must emit a structured log event with at least:
  - component/service
  - user id
  - target date
  - error class/message
  - marker that local activation fallback was used
- If an existing V2 debug/meta field is available, populate it too; otherwise structured log is enough for W5.

Add tests or log assertions proving the marker is emitted.

### 6. Replace false-positive tests with real service integration tests

Remove or rewrite tests that only call mocks directly.

Required test coverage:

- TodayService dual-run:
  - patches `get_solarsage_client`;
  - `get_activation_layer()` returns a sidecar layer containing non-W2 technique `annual_profection`;
  - `ActivationLayerService.build()` / `DayScoringRuntimeService.compute()` receives an activation layer containing that technique.
- Calendar computed status path:
  - calls `get_activation_layer()` when V2 may be computed.
- V1-only:
  - no sidecar activation-layer call.
- Cache:
  - duplicate same date/profile rows with different hashes do not produce `MultipleResultsFound`;
  - lookup/upsert uses current `cache_key_hash`.
- Semantic:
  - stale/wrong identity misses and recomputes.

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
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/10_rework_03_report.md
```

Include:

- changed files;
- exact proof that Calendar payload cache validates versioned identity;
- exact proof that Calendar semantic cache validates all required fields;
- exact proof that TodayService and CalendarService pass complete current location when available;
- exact proof that shadow fail-open is logged and enabled mode fails loudly;
- exact proof that integration tests exercise real service paths, not direct mock calls;
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
  -d '{"prompt":"Wave W5 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/09_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
