# W8 Rework 01 TZ - Produce a Real Final Acceptance Audit

## Context

Read first:

- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/00_TZ.md`
- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/02_arch_review.md`
- `docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md`

Work on branch `main`.

Do not push. Do not deploy. Do not use `sudo`.

This remains audit-only. Do not make product/code fixes.

## Required First Step

Restore the deleted W8 TZ:

```bash
git restore -- docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/00_TZ.md
```

Then verify:

```bash
git status --short --branch
```

`00_TZ.md` must not be deleted.

## Required Rework

Rewrite the W8 final acceptance audit report so that it complies with `00_TZ.md`.

Required:

1. Include all 49 checklist items from `00_TZ.md`.
2. Use only these statuses: `PROVEN`, `GAP`, `WEAK`, `MISSING`.
3. Use final verdict:
   - `ACCEPTANCE_READY` only if all 49 are `PROVEN`;
   - otherwise `REWORK_REQUIRED`.
4. Run every required command in `00_TZ.md`.
5. If any command cannot run, record the exact reason and mark affected rows `WEAK`, `MISSING`, or `GAP`.
6. Do not replace command execution with "file exists" evidence for behavior claims.
7. Correct process history:
   - initial W8 attempt used `sudo rm -rf`;
   - W8 Rework 01 must not use sudo.

## Commands That Must Appear In The Report

The report must include exact output summaries for each of these:

```bash
git status --short --branch
git log --oneline -12
python3 scripts/check_audit_golden.py
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_logging_guardrails.py
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff -- artifacts/audit/2026-07-08
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_astronomy_oracle.py tests/test_semantic_contexts.py tests/test_today_concrete_advice_consistency.py tests/test_activation_layer_service.py tests/test_activation_schema.py tests/test_scoring_v2_service.py tests/test_scoring_v2_runtime_flags.py tests/test_today_cache_v2_key.py tests/test_today_service_v2_dual_run.py tests/test_calendar_v2_dual_run.py tests/test_today_v2_payload.py tests/test_semantic_v2_service.py tests/test_llm_claim_validator.py tests/test_today_meta_versions.py tests/test_day_endpoints.py tests/test_calendar_endpoints.py -q
cd apps/solarsage && source venv/bin/activate && python -m pytest tests -q
pnpm contracts:generate
pnpm typecheck
npx vitest run __tests__/contracts/today.test.ts __tests__/lib/adapt-payload.test.ts __tests__/components/TodayScreen.test.tsx
E2E_BASE_URL=http://localhost:3002 npx playwright test e2e/mock-visual/day-v2.spec.ts --project=mobile
rg -n 'transit_to_natal|transit_to_angle|transit_to_lot|annual_profection|monthly_profection|firdar_major|firdar_minor|solar_return|lunar_return|solar_arc|secondary_progression|eclipse_window' apps scripts packages __tests__ artifacts/audit docs/rollout
rg -n 'dominance_capped|convergence|technique_family|score_breakdown|activation_layer_version|scoring_canon_version|SOLARSAGE_V2_ENABLED|SOLARSAGE_V2_DUAL_RUN|SOLARSAGE_V2_FRONTEND_ENABLED' apps scripts packages __tests__ docs/rollout
rg -n 'Moon opposition Pluto|Moon opposite Pluto|Transit_Moon|Natal_|Transit_' apps __tests__ packages artifacts/audit/2026-07-08
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

For privacy `rg` commands, no output is a pass. For static evidence `rg` commands, matches are expected; summarize relevant matches and classify any ambiguous user-facing labels.

## Report Required

Overwrite/update:

`docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md`

Also write:

`docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/04_rework_01_report.md`

`04_rework_01_report.md` should summarize:

- what changed in the audit report;
- exact commands run;
- whether `00_TZ.md` was restored;
- final verdict;
- commit SHA;
- push/deploy status;
- confirmation that W8 Rework 01 used no sudo.

## Commit

Commit only W8 docs/report changes.

Suggested message:

```bash
git commit -m "docs(w8): rework final acceptance audit evidence"
```

## Callback

At the very end, after report and commit, run:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W8 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/04_rework_01_report.md. Audit: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/01_final_acceptance_audit_report.md. Review: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w8-final-acceptance-audit/03_rework_01_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
