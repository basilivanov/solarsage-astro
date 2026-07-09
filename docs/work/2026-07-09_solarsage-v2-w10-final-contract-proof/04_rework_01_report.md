# W10 Rework 01 Report

Date: 2026-07-09
Base reviewed commit: `ed2d2e6`
Final rework commit: `d895d48`
Branch: `main`
Push: NOT_ATTEMPTED
Deploy: NOT_ATTEMPTED
Remote CI: REMOTE_CI_NOT_AVAILABLE

## Process constraints

- Used normal git index only (no alternate `GIT_INDEX_FILE`).
- No `sudo`.
- No `.git/index` deletion/repair.
- No `git reset --hard` / `git checkout --`.
- No push/deploy.

## Fixes

### P0 — V2 identity with null body blocked on schema + cache paths

1. `apps/api/app/schemas/today.py`
   - Added `TodayPayload.validate_v2_identity_requires_body`.
   - Rejects explicit `payload_version="today.v2"` with `v2=None`.
   - Rejects explicit `frontend_payload_version=2` with `v2=None`.
   - V1 / missing explicit V2 identity still allows `v2=None`.

2. `apps/api/app/services/today_service.py`
   - `_get_cached_payload()` treats legacy bad V2 cache rows as miss (`return None`) when:
     - `payload_version == today.v2` and `v2 is None`, or
     - `frontend_payload_version == 2` and `v2 is None`.
   - Construction failures on invalid cache rows also return `None` (no request crash).
   - V1 cached rows with `v2=None` remain valid hits.

### P1 — Frozen-baseline mapping proof

Extended `test_frozen_mode_does_not_call_today_service` to assert:

- root `activation_evidence_mapping.json` exists
- debug `activation_evidence_mapping.json` exists
- status is `frozen_baseline_not_live`
- frozen mode remains non-live

Live audit unmapped/missing-v2 checks were not weakened.

## Files changed

- `apps/api/app/schemas/today.py`
- `apps/api/app/services/today_service.py`
- `apps/api/tests/test_today_meta_versions.py`
- `apps/api/tests/test_audit_today_modes.py`
- `docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/04_rework_01_report.md`

## Verification

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  -q
```

Result: **52 passed**

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_profections.py -q
```

Result: **15 passed, 1 warning**

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

Result:

- contracts generate: **PASSED**
- contracts diff: **zero**
- typecheck: **PASSED**

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
git status --short --branch
```

Result: recorded after commit.

## Explicit statements

- Push: NOT_ATTEMPTED
- Deploy: NOT_ATTEMPTED
- Remote CI: REMOTE_CI_NOT_AVAILABLE
- Normal git index used.
- Final status expected clean except known untracked local files (`.grace/`, `grace.db`, `skills/`, superpowers plan).

## Callback command

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W10 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/03_rework_01_TZ.md. Branch: main. Commit: d895d48. Push: NOT_ATTEMPTED"}'
```
