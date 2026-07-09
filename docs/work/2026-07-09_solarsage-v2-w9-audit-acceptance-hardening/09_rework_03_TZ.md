# W9 Rework 03 TZ

Status: READY_FOR_CODER
Date: 2026-07-09
Base reviewed commit: `127d0b1`
Architect review: `docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/08_rework_02_review.md`

## Goal

Fix the Rework 02 whitespace gate failure only. Do not change business logic, audit behavior, scoring formulas, frontend UI, contracts, or unrelated docs.

## Required Fix

Remove the extra blank line at EOF from:

- `apps/api/app/services/today_service.py`
- `apps/api/tests/test_today_meta_versions.py`

The expected result is:

```bash
git diff --check 92fa2fd..HEAD
git show --check HEAD
```

Both commands must be clean.

## Required Verification

Run:

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

Then run:

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
docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/10_rework_03_report.md
```

Include:

- final code/tests commit SHA;
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
  -d '{"prompt":"Wave W9 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w9-audit-acceptance-hardening/09_rework_03_TZ.md. Branch: main. Commit: <COMMIT_SHA>. Push: NOT_ATTEMPTED"}'
```
