# Wave W0 Rework 07 TZ

You are the coder agent. Work in `/opt/solarsage-astro` on branch `main`.

Read first:
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/20_rework_06_review.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/18_rework_06_TZ.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/19_rework_06_report.md`

Do not push or deploy.

## Required Work

1. Fix the failing claims gate.
   - The exact `rg` command from `18_rework_06_TZ.md` must return no matches / exit `1`.
   - Fix both committed baseline `artifacts/audit/2026-07-08/14_claims_audit.md` and the generator in `scripts/audit_today.py`.
   - Do not narrow the command and do not exclude the historical section in the report.

2. Add the missing regression tests.
   - Test default audit fail-fast for missing baseline before canonical writes and before any TodayService/LLM generation path.
   - Test invalid baseline fail-fast before artifact writes.
   - Test live output routing writes only under `live/<timestamp>/` and leaves canonical root/debug untouched.
   - Test `SemanticService.build_why_contexts(...)` does not emit the relationship outreach bullet when `relationships_partnership` is below the avoid threshold.
   - Keep tests fast and isolated. It is acceptable to factor pure helpers from `scripts/audit_today.py`.

3. Make baseline validation happen before writes.
   - In default mode, load and minimally validate `11_final_today_payload.json` before `out_dir/debug` writes, DB/session work, sidecar calls, or oracle calls.
   - If missing or invalid, exit non-zero with no canonical/debug artifact writes.

4. Update the report.
   - Write `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/22_rework_07_report.md`.
   - Do not claim a gate passed if the exact command did not pass.

## Verification

Run and report exact results:

```bash
apps/api/.venv/bin/python -m pytest apps/api/tests/test_astronomy_oracle.py apps/api/tests/test_semantic_contexts.py apps/api/tests/test_today_concrete_advice_consistency.py apps/api/tests/test_today_concrete_advice.py apps/api/tests/test_day_endpoints.py apps/api/tests/test_calendar_endpoints.py -q
cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py tests/test_services.py -q
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
git diff --exit-code -- artifacts/audit/2026-07-08
apps/api/.venv/bin/python scripts/audit_today.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08 --live-llm-sample
git diff --exit-code -- artifacts/audit/2026-07-08
rm -rf artifacts/audit/2026-07-08/live/
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' artifacts/audit/2026-07-08/14_claims_audit.md artifacts/audit/2026-07-08/11_final_today_payload.json; test $? -eq 1
git diff 2f9173f..HEAD --check
git show --check HEAD
git status --short --branch
```

Also run the new targeted tests directly and report their command/results.

Commit all intended changes. Do not push/deploy.

When done, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 07 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/22_rework_07_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/20_rework_06_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/21_rework_07_TZ.md. Branch: main. Commit: <HEAD>. Push: NOT_ATTEMPTED"}'
```
