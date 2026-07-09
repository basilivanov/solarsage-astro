# W10 Rework 01 TZ

Status: READY_FOR_CODER
Date: 2026-07-09
Base reviewed commit: `ed2d2e6`
Architect review: `docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/02_arch_review.md`

## Goal

Close the remaining W10 proof gaps without expanding scope.

Do not change astrology formulas, scoring formulas, frontend UI, deployment, or unrelated docs.

## Required Fixes

### 1. Enforce V2 payload/body invariant for cached and schema paths

W10 hard stop forbids:

```text
payload_version=today.v2 AND payload.v2 is null
frontend_payload_version=2 AND payload.v2 is null
```

Current fresh-build path checks this, but cached/schema paths still allow it.

Implement:

- schema-level validator in `apps/api/app/schemas/today.py` if possible without circular imports;
- cached-read guard in `TodayService._get_cached_payload()` that treats old bad cached rows as cache misses before returning to the caller.

Recommended policy:

- `TodayPayload` validation should reject explicit V2 identity with `v2=None`.
- `_get_cached_payload()` should not crash user requests on old bad cache rows. It should detect the bad cached JSON before constructing/returning `TodayPayload` and return `None` so the service rebuilds a fresh payload.
- V1 payloads with `v2=None` must remain valid.
- Payloads with missing/legacy `payload_version` must not be rejected unless they explicitly declare V2 identity.

Add regression coverage:

1. `TodayPayload` rejects explicit `payload_version="today.v2"` with `v2=None`.
2. `TodayPayload` rejects explicit `frontend_payload_version=2` with `v2=None`.
3. `_get_cached_payload()` returns `None` for a matching V2 cache row with `v2=None`.
4. `_get_cached_payload()` still returns V1 cached rows with `v2=None`.

### 2. Add frozen-baseline mapping proof test

Extend audit tests so frozen-baseline mode asserts:

- root `activation_evidence_mapping.json` exists;
- debug `activation_evidence_mapping.json` exists;
- mapping status is `frozen_baseline_not_live` or equivalent non-live status;
- frozen mode does not claim live production proof through mapping.

Do not weaken live-mode mapping checks.

### 3. Git/index process

Do not use:

- alternate `GIT_INDEX_FILE`;
- `sudo`;
- `.git/index` deletion or repair;
- `git reset --hard`;
- `git checkout --`;
- push/deploy.

If permissions block normal git, stop and report. The architect will fix ownership.

## Required Verification

Run at minimum:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py \
  -q
```

```bash
cd apps/solarsage && source venv/bin/activate && python -m pytest tests/test_profections.py -q
```

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
git status --short --branch
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/04_rework_01_report.md
```

Include:

- final commit SHA;
- exact files changed;
- exact commands/results;
- push/deploy status;
- remote CI status;
- statement that normal git index was used and the final `git status --short --branch` is clean except known untracked local files.

## Callback

If callback service is available, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W10 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w10-final-contract-proof/03_rework_01_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```

If callback service is unavailable, leave the same callback command in the report and stop at a clean committed state.
