# W5 Rework 05 TZ — Add Real Integration Tests and Honest Gates

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W5 Rework 04
Push/deploy: do not push or deploy.

## Goal

Resolve all findings from:

```text
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/14_rework_04_review.md
```

This rework should be mostly tests and report/verification. Do not change product behavior unless a test exposes a real bug.

## Required Work

### 1. Replace the TodayService false-positive test

Remove or rewrite:

```text
apps/api/tests/test_today_meta_versions.py::test_sidecar_activation_layer_fetched_when_v2_computed
```

It currently only calls a mock directly and proves nothing about TodayService.

Required TodayService tests:

- Dual-run path:
  - create a real test user/profile in DB;
  - set `settings.solarsage_v2_dual_run=True`, `settings.solarsage_v2_enabled=False`;
  - patch `app.services.today_service.get_solarsage_client`;
  - mock `get_activation_layer()` to return an activation layer containing non-W2 technique `annual_profection`;
  - mock/patch dependencies as needed using the existing `test_today_service_fresh_payload_activation_layer_wiring` pattern;
  - prove `get_activation_layer()` was awaited by `TodayService`;
  - prove `DayScoringRuntimeService.compute()` received an `activation_layer` containing the `annual_profection` activation.
- V1-only path:
  - with both V2 flags false, prove TodayService does not call `get_activation_layer()`.
- Shadow fail-open:
  - dual-run true, enabled false;
  - make `get_activation_layer()` raise;
  - prove service returns V1-selected payload/output;
  - patch/capture `app.services.today_service.log_event` and prove the fallback marker is emitted.
- V2-enabled fail-loud:
  - enabled true;
  - make `get_activation_layer()` raise;
  - prove TodayService raises and does not log `"using local fallback"`.
- Current location:
  - complete `current_lat/current_lon/current_tz` is passed to `get_activation_layer()`;
  - missing `current_tz` omits `current_location`.

### 2. Add CalendarService service-path tests

Required CalendarService tests:

- Dual-run computed status path calls `get_activation_layer()` when V2 may be computed.
- V1-only path does not call `get_activation_layer()`.
- Shadow sidecar failure returns V1 status/`None` according to existing Calendar fallback contract and emits the structured fallback log marker.
- V2-enabled sidecar failure raises/propagates instead of returning `None`.
- Complete current location is passed; incomplete current location is omitted.

Use `_compute_and_cache_day_status()` directly if that is the narrowest stable surface. Patch dependencies instead of hitting the real sidecar.

### 3. Add DB-level cache identity tests

Add tests that exercise actual DB rows and service lookup/upsert behavior, not only pure hash construction:

- `TodayService._get_cached_payload()`:
  - insert two `TodayPayloadCache` rows with same user/date/profile and different `cache_key_hash`;
  - lookup with the current key returns only the matching row and does not raise `MultipleResultsFound`;
  - stale empty-hash row misses.
- `TodayService._cache_payload()`:
  - upsert updates only the matching `cache_key_hash` row and never mutates a different-hash row.
- `CalendarService._get_cached_day_status()`:
  - stale payload row with wrong or empty `cache_key_hash` misses;
  - semantic row with wrong `activation_layer_version` misses;
  - semantic row with matching identity hits.

### 4. Keep cache-key tests explicit

Extend pure cache-key tests if needed:

- `activation_layer_version=None` and `"al-1.0"` produce different hashes.
- `"al-1.0"` and another version produce different hashes.
- `expected_cache_identity()` has non-None `activation_layer_version`.

### 5. Verification discipline

Run final verification commands without `tail`. Do not use `tail` in the report evidence.

If full API suite still has the known oracle failure, report it as:

```text
Full API suite: FAILED only tests/test_astronomy_oracle.py::test_audit_live_isolates_output — known external sidecar/oracle dependency. Non-oracle API tests passed: <exact evidence>.
```

Do not summarize it as green.

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
docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/16_rework_05_report.md
```

Include:

- changed files;
- exact list of new/replaced tests;
- exact proof that TodayService and CalendarService integration tests exercise real service paths;
- exact proof that DB cache identity tests cover duplicate/wrong-hash rows;
- exact verification outputs, without `tail`;
- exact status of the known full-suite oracle failure if still present;
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
  -d '{"prompt":"Wave W5 Rework 05 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/16_rework_05_report.md. Review: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/14_rework_04_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w5-api-cache-dual-run/15_rework_05_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```

