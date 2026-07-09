# W8 Rework 02 TZ - Close Final Contracts, Typecheck, and E2E Evidence

## Context

Read first:

- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/05_rework_01_review.md`
- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md`
- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/04_rework_01_report.md`

Work on branch `main`.

Do not push. Do not deploy. Do not use `sudo`.

This remains audit-only. Do not make product/code fixes.

The architect already corrected ownership of:

- `packages/contracts/_generated.ts`
- `test-results/`
- `playwright-report/`

## Required Commands

Run from repo root:

```bash
stat -c '%A %U:%G %n' packages/contracts/_generated.ts test-results playwright-report
pnpm contracts:generate
git diff -- packages/contracts/openapi.json packages/contracts/_generated.ts
pnpm typecheck
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
git status --short --branch
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
```

## Decision Rules

### Contracts generation

- If `pnpm contracts:generate` passes and produces no tracked diff, item 8 may become `PROVEN`.
- If it produces a tracked diff, do not commit the generated product files in this audit-only rework. Mark item 8 `GAP`, include the diff summary, and keep final verdict `REWORK_REQUIRED`.
- If it fails, mark item 8 `MISSING` or `GAP` with exact error.

### Typecheck

- If `pnpm typecheck` passes, item 33 may become `PROVEN`.
- If it fails, keep item 33 `MISSING/GAP` and report exact errors.

### E2E

- If Playwright passes, item 36 may become `PROVEN`.
- If it fails because of an actual UI/test assertion, mark item 36 `GAP`.
- If it fails because service 3002 is unavailable or another external precondition is missing, mark item 36 `WEAK/MISSING` with exact evidence.

### Final verdict

- `ACCEPTANCE_READY` only if all 49 matrix rows are `PROVEN`.
- Otherwise `REWORK_REQUIRED`.

## Report Updates

Update:

`docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md`

Write:

`docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/07_rework_02_report.md`

The Rework 02 report must include:

- ownership state;
- exact output of the three previously blocked commands;
- generated contract diff status;
- updated statuses for items 8, 33, and 36;
- final 49-row totals;
- final verdict;
- final git status;
- commit SHA;
- push/deploy status;
- confirmation that no sudo was used.

## Commit

Commit only W8 docs/report changes.

Do not commit generated contract changes or product code changes in this audit-only rework.

Suggested message:

```bash
git commit -m "docs(w8): close final acceptance evidence gaps"
```

## Callback

At the very end, after report and commit, run:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W8 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/07_rework_02_report.md. Audit: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md. Review: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/06_rework_02_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
