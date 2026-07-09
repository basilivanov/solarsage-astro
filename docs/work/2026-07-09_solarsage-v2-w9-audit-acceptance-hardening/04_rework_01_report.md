# W9 Rework 01 Report

Date: 2026-07-09
Base reviewed commit: `ebb1898`
Final rework commit: `ab8ca23`
Code/tests payload commit in history: `2d2119f` (same message); tip includes report SHA correction.
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE

## Process constraints

- No `sudo` used in this rework.
- No `.git/index` deletion.
- No push/deploy.
- No product scope expansion beyond review findings.

## Findings fixed

### 1. Whitespace gate (P0)

Removed trailing whitespace in `01_agent_report.md` (lines 3–7).

### 2. Report commit SHA (P0)

Updated `01_agent_report.md` Commit SHA section to the final rework commit after commit.

### 3. Frozen-baseline oracle payload (P1)

In `scripts/audit_today.py` frozen mode now writes the validated baseline to:

- `debug/final_today_payload.json`
- `debug/final_today_payload.normalized.json`

before `run_oracles()`.

Regression: `tests/test_audit_today_modes.py::test_frozen_mode_does_not_call_today_service` asserts payload exists inside the oracle mock and on disk.

### 4. V1 version identity regression (P1)

`TodayService` now selects meta/cache identity by **selected scoring path**:

- V1 selected: `calculation_version="1"`, `scoring_version=1`, `payload_version="today.v1"`, `frontend_payload_version=1`
- V2 selected: `ss-calc-1.1.0` / `al-1.0` / `ss-scoring-2.0` / frontend+payload V2 when enabled

Local fallback activation-layer calculation version no longer overwrites V1 payload/cache identity.

Regression: `tests/test_today_meta_versions.py::test_v1_only_payload_and_cache_identity_not_polluted_by_v2_calc`.

## Files changed

- `scripts/audit_today.py`
- `apps/api/app/services/today_service.py`
- `apps/api/tests/test_audit_today_modes.py`
- `apps/api/tests/test_today_meta_versions.py`
- `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/01_agent_report.md`
- `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/04_rework_01_report.md` (this file)

## Verification commands and results

### Backend focused tests

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

Result: **68 passed**

### Sidecar focused tests

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

Result: **144 passed, 1 warning**

### Gates

```bash
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
```

Result: **all PASSED**

### Contracts / typecheck

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- `pnpm contracts:generate` **FAILED** with `EACCES` on root-owned `packages/contracts/_generated.ts` (`-rw------- root:root`).
- No product contract content change intended in this rework.
- `pnpm typecheck` **FAILED** transitively because `_generated.ts` is unreadable (same ownership issue).
- Per rework TZ process constraints, **no sudo** was used to repair ownership. This is an environment blocker, not a code regression from Rework 01.

### Whitespace

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Recorded after final commit (must pass once trailing whitespace fix is committed).

## Explicit statements

- Push: **NOT_ATTEMPTED**
- Deploy: **NOT_ATTEMPTED**
- Remote CI: **REMOTE_CI_NOT_AVAILABLE**
- Process: **no sudo**, **no `.git/index` deletion**

<!-- rework01-commit: ab8ca23 -->
