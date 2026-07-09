# W9 Rework 02 TZ

Status: READY_FOR_CODER
Date: 2026-07-09
Base reviewed commit: `eee6346`
Architect review: `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/05_rework_01_review.md`

## Goal

Fix the remaining W9 version-identity blocker only. Do not change audit mode behavior, Feb 29 logic, scoring formulas, frontend UI, or unrelated docs.

## Required Fix

### V2-selected identity must be V2 even if frontend flag is off

In `TodayService.get_today_payload()`, `v2_selected` currently still allows `payload_version="today.v1"` and `frontend_payload_version=1` when `settings.solarsage_v2_frontend_enabled` is false.

Required behavior:

- If selected scoring version is `ss-scoring-2.0`, payload/cache identity must be:
  - `calculation_version="ss-calc-1.1.0"`
  - `activation_layer_version="al-1.0"`
  - `scoring_version="ss-scoring-2.0"`
  - `payload_version="today.v2"`
  - `frontend_payload_version=2`
- If selected scoring version is legacy `1`, payload/cache identity must remain:
  - `calculation_version="1"`
  - `scoring_version=1`
  - `payload_version="today.v1"`
  - `frontend_payload_version=1`

The selected scoring path is the source of truth. Do not key V2 payload/cache identity off `SOLARSAGE_V2_FRONTEND_ENABLED`.

## Required Regression

Add/extend tests in `apps/api/tests/test_today_meta_versions.py`:

1. Keep the Rework 01 V1-only regression.
2. Add a V2-selected regression with:
   - `settings.solarsage_v2_enabled=True`;
   - `settings.solarsage_v2_frontend_enabled=False`;
   - mocked runtime/scoring path returning selected scoring version `ss-scoring-2.0`;
   - returned `TodayPayload.meta.payload_version == "today.v2"`;
   - returned `TodayPayload.meta.frontend_payload_version == 2`;
   - cache key write identity matches the payload meta.

Use the existing test style in the same file. Keep it focused and deterministic.

## Required Verification

Run at minimum:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_today_meta_versions.py \
  tests/test_today_cache_v2_key.py \
  tests/test_audit_today_modes.py \
  tests/test_audit_activation_sidecar_artifacts.py -q
```

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

If time permits, also rerun:

```bash
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
```

## Process Constraints

Do not use:

- `sudo`
- `.git/index` deletion or repair commands
- `git reset --hard`
- `git checkout --`
- push/deploy

If permissions block you, stop and report. The architect will fix ownership externally.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/07_rework_02_report.md
```

Include:

- final commit SHA;
- exact files changed;
- exact commands/results;
- push/deploy status;
- process statement: no sudo, no `.git/index` deletion.

## Callback

After commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W9 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/06_rework_02_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```
