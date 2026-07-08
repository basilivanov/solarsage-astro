# Wave W0 Rework 03 TZ

Source review:

`docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/08_rework_02_review.md`

Branch: `main`
Push/deploy: do not push/deploy before architect acceptance

## Task

Resolve the remaining W0 report/audit hygiene issues. Do not change W1-W7 scope. Do not change scoring semantics.

## Mandatory Changes

1. Fix `scripts/audit_today.py` claims extraction:
   - support current snake_case payload keys;
   - keep camelCase fallback only as compatibility;
   - generated `14_claims_audit.md` must include:
     - real lunar phase fact (`Убывающая Луна 44%` for Basil 2026-07-08);
     - real top flags;
     - all 12 concrete advice rows.
2. Add regression coverage:
   - a test or script-level check that fails if claims report renders `N/A` for fields present in the payload.
3. Remove trailing whitespace from the final tree:
   - `apps/api/tests/test_astronomy_oracle.py`;
   - `scripts/audit_today.py`;
   - `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/05_rework_01_review.md`;
   - any other touched files.
4. Regenerate/commit canonical audit artifacts after the claims fix.
5. Write report:
   `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/10_rework_03_report.md`.

## Required Verification

Run:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py \
  -q
```

Run:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_ephemeris_retrograde.py \
  tests/test_services.py \
  -q
```

Run:

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Run:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

Then verify:

```bash
jq -r '.meta.content_version, .meta.cached' artifacts/audit/2026-07-08/11_final_today_payload.json
jq '.moon_phase, .retrograde_flag_pass' artifacts/audit/2026-07-08/13_astronomy_oracle_summary.json
jq '.comparison.day_status, .comparison.top_signals' artifacts/audit/2026-07-08/12_scoring_oracle_comparison.json
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\\| N/A \\| N/A \\| N/A \\|' artifacts/audit/2026-07-08/14_claims_audit.md
```

The `rg` command must return no matches.

Also run:

```bash
git diff 2f9173f..HEAD --check
git show --check HEAD
git status --short --branch
```

Final `git status` must show only known unrelated untracked files:

```text
.grace/
grace.db
skills/
docs/superpowers/...
```

## Commit and Callback

Commit intended changes only. Do not push/deploy.

Callback:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 03 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/10_rework_03_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/08_rework_02_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/09_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
