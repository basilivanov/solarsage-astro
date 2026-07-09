# W5 Rework 06 TZ — Finish Missing Service-Path Coverage

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 05 (`de74ad4`)
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/17_rework_05_review.md
```

This is a test/verification rework. Do not change product behavior unless a new real service-path test exposes a product bug. Keep edits tight.

## Required Work

### 1. Complete CalendarService service-path tests

Add tests that exercise `CalendarService._compute_and_cache_day_status()` itself.

Required cases:

- Dual-run mode:
  - `settings.solarsage_v2_dual_run=True`, `settings.solarsage_v2_enabled=False`;
  - real test user/profile in DB;
  - `CalendarService._request_profile` set to that profile;
  - patched `app.services.calendar_service.get_solarsage_client`;
  - sidecar `get_activation_layer()` returns a layer containing non-W2 technique `annual_profection`;
  - assert `get_activation_layer()` was awaited by CalendarService;
  - assert runtime `compute()` received an `activation_layer` containing `annual_profection`.
- V1-only mode:
  - both flags false;
  - assert `get_activation_layer()` is not awaited.
- Shadow fail-open:
  - dual-run true, enabled false;
  - `get_activation_layer()` raises;
  - assert method returns the existing Calendar fallback contract (`None` or V1 status, whichever current code actually defines);
  - capture `app.services.calendar_service.log_event` and assert `scoring.v2_diff` fallback marker is emitted.
- V2-enabled fail-loud:
  - enabled true;
  - `get_activation_layer()` raises;
  - assert exception propagates and no fallback log is emitted.
- Current location:
  - with complete `current_lat/current_lon/current_tz`, assert `get_activation_layer()` receives `current_location={"lat": ..., "lon": ..., "tz": ...}`;
  - with missing `current_tz`, assert `current_location=None`.

### 2. Complete TodayService integration assertions

Fix `test_today_service_dual_run_fetches_sidecar_activation` so it proves the actual runtime receives the non-W2 activation:

- Patch `app.services.today_service.DayScoringRuntimeService` so `compute()` call kwargs can be inspected.
- Do not return an empty activation layer if the assertion is about `annual_profection`.
- Assert `compute(..., activation_layer=...)` contains an activation with `technique == "annual_profection"`.

Add TodayService current-location tests:

- complete `current_lat/current_lon/current_tz` is passed to `get_activation_layer()`;
- missing `current_tz` omits `current_location`.

Use the pytest `monkeypatch` fixture instead of manual `pytest.MonkeyPatch()` objects unless there is a specific reason. If manual monkeypatch remains, guarantee cleanup in `finally`.

### 3. Replace DB direct-select tests with real service helper tests

In `apps/api/tests/test_today_cache_v2_key.py`, keep pure hash tests, but for service behavior call the service helpers:

- `TodayService._get_cached_payload()`:
  - insert two `TodayPayloadCache` rows with same user/date/profile and different `cache_key_hash`;
  - use a minimal valid `TodayPayload` JSON in each row;
  - call `_get_cached_payload(user_id, target_date, profile_hash, cache_key)`;
  - assert it returns only the matching row, sets `meta.cached=True`, and does not raise `MultipleResultsFound`;
  - stale empty-hash row misses through `_get_cached_payload()`.
- `TodayService._cache_payload()`:
  - create two rows with same user/date/profile but different hashes;
  - call `_cache_payload()` with one hash and a minimal valid `TodayPayload`;
  - assert only the matching hash row is updated and the other row is unchanged.
- `CalendarService._get_cached_day_status()`:
  - wrong/empty `TodayPayloadCache.cache_key_hash` misses;
  - semantic row with wrong `activation_layer_version` misses;
  - semantic row with fully matching identity hits.

Do not leave unused service variables or comments saying a required service helper was intentionally avoided.

### 4. Finish pure cache-key coverage

Add explicit hash test:

- `activation_layer_version="al-1.0"` and another non-null version produce different hashes.

### 5. Clean whitespace honestly

- Remove trailing blank lines at EOF in every file you touch.
- Re-run:

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
```

If historical docs still fail because of older commits, report exact files. New/touched implementation/test files must be clean.

## Required Verification

Run and report exact commands/results, without `tail`:

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
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/19_rework_06_report.md
```

Include:

- changed files;
- exact list of new/replaced tests;
- proof that TodayService and CalendarService tests exercise real service paths;
- proof that DB cache identity tests call real service helper methods;
- exact verification outputs, without `tail`;
- full API suite status;
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
  -d '{"prompt":"Wave W5 Rework 06 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/19_rework_06_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/17_rework_05_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/18_rework_06_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
