# W9 Rework 01 TZ

Status: READY_FOR_CODER
Date: 2026-07-09
Base reviewed commit: `ebb1898`
Architect review: `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/02_arch_review.md`

## Goal

Fix only the W9 acceptance blockers found in architect review. Do not broaden scope, do not retune scoring, do not change frontend UI, do not push, do not deploy.

## Must Fix

### 1. Whitespace gate

Remove trailing whitespace in `01_agent_report.md`.

Required commands:

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Both must pass after your new commit.

### 2. Report commit SHA

`01_agent_report.md` currently says `2e43bcf`, but actual reviewed HEAD was `ebb1898`.

After your rework commit, update `01_agent_report.md` so it records the real final rework commit SHA. No stale SHA, no placeholder.

### 3. Frozen baseline oracle payload

In `scripts/audit_today.py`, frozen-baseline mode must materialize the validated baseline payload under `debug/` before oracle runners execute.

Required behavior:

- `--mode frozen-baseline` validates existing root `11_final_today_payload.json`.
- It writes that exact validated payload to `debug/final_today_payload.json`.
- Prefer also writing `debug/final_today_payload.normalized.json` for shape parity with live mode.
- `artifact_source.json` must still say:
  - `mode=frozen-baseline`
  - `final_payload_source=committed_baseline_fixture`
- `make audit-day-freeze` must not depend on stale debug payload files from previous runs.

Add or update a regression test that proves frozen mode writes `debug/final_today_payload.json` before or during the oracle path. The test must fail on the current `ebb1898` behavior.

### 4. V1 version identity regression

Fix V1-only TodayPayload/cache identity so V1 is not polluted with the V2 calculation version.

Required behavior:

- V1-only selected path:
  - `calculation_version="1"`
  - `scoring_version=1`
  - `payload_version="today.v1"`
  - `frontend_payload_version=1`
- V2 selected path:
  - `calculation_version="ss-calc-1.1.0"`
  - `activation_layer_version="al-1.0"`
  - `scoring_version="ss-scoring-2.0"`
  - `payload_version="today.v2"`
  - `frontend_payload_version=2`

Do not let `ActivationLayerService.build()` blindly force V2 calculation identity into a V1 payload/cache key.

Add regression coverage for:

- V1-only `TodayService.get_today_payload()` meta keeps legacy calculation/scoring/payload/frontend versions.
- V1-only cache write identity matches the payload meta identity.

Keep existing sidecar V2 constants and tests intact.

### 5. Process constraints

Do not use:

- `sudo`
- `rm -f .git/index`
- `git reset --hard`
- `git checkout --`
- push/deploy

If a permission issue blocks you, stop and write it in the report.

## Required Verification

Run at minimum:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  tests/test_today_cache_v2_key.py \
  tests/test_today_meta_versions.py \
  tests/test_activation_layer_contract.py \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_scoring_v2_runtime_flags.py -q
```

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest \
  tests/test_activation_layer_endpoint.py \
  tests/test_activation_schema.py \
  tests/test_activation_transits.py \
  tests/test_profections.py \
  tests/test_firdar.py \
  tests/test_solar_return.py \
  tests/test_lunar_return.py \
  tests/test_secondary_progressions.py \
  tests/test_solar_arc.py \
  tests/test_eclipse_window.py \
  tests/test_activation_layer_family_coverage.py -q
```

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

If you run additional tests, include them in the report.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/04_rework_01_report.md
```

The report must include:

- final commit SHA;
- files changed;
- exact commands and results;
- explicit statement that no push/deploy was attempted;
- explicit statement whether `REMOTE_CI_NOT_AVAILABLE` still applies;
- process statement: no sudo, no `.git/index` deletion.

## Commit and Callback

Commit intended W9 rework changes only.

After commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W9 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/03_rework_01_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```
