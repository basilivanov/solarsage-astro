# W9 Rework 02 Report

Date: 2026-07-09
Base reviewed commit: `eee6346` / request tip before this rework: `4e5efb0`
Final rework code/tests commit: `d1dfec7`
Evidence docs tip: current main HEAD / callback SHA after this report package.
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE

## Process constraints

- No `sudo` used.
- No `.git/index` deletion or repair.
- No `git reset --hard` / `git checkout --`.
- No push/deploy.
- Scope limited to V2-selected version identity + regression + this report.

## Fix

In `TodayService.get_today_payload()`, selected scoring version is the source of truth for payload/cache identity.

When selected scoring is `ss-scoring-2.0` (`v2_selected`):

- `calculation_version=ss-calc-1.1.0`
- `activation_layer_version=al-1.0` (from activation layer, fallback constant)
- `scoring_version=ss-scoring-2.0`
- `payload_version=today.v2`
- `frontend_payload_version=2`

This no longer depends on `SOLARSAGE_V2_FRONTEND_ENABLED`.

When selected scoring is legacy `1`:

- `calculation_version=1`
- `scoring_version=1`
- `payload_version=today.v1`
- `frontend_payload_version=1`

## Files changed

- `apps/api/app/services/today_service.py`
- `apps/api/tests/test_today_meta_versions.py`
- `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/07_rework_02_report.md`

## Regression

Added:

`test_v2_selected_identity_even_if_frontend_flag_off`

Covers:

- `solarsage_v2_enabled=True`
- `solarsage_v2_frontend_enabled=False`
- runtime selected scoring `ss-scoring-2.0`
- meta and cache key write identity are full V2

Kept Rework 01 V1-only regression.

## Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py -q
```

Result: **38 passed**

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Result: **clean** (no trailing whitespace reported)

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- contracts generate: **PASSED**
- contracts diff: **zero**
- typecheck: **PASSED**

## Explicit statements

- Push: NOT_ATTEMPTED
- Deploy: NOT_ATTEMPTED
- Remote CI: REMOTE_CI_NOT_AVAILABLE
- Process: no sudo, no `.git/index` deletion
