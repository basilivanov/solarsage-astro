# Wave W0 Rework 08 TZ

You are the coder agent. Work in `/opt/solarsage-astro` on branch `main`.

Read first:
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/23_rework_07_review.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/21_rework_07_TZ.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/22_rework_07_report.md`

Do not push or deploy.

## Required Work

1. Strengthen the live isolation regression test.
   - The test must fail if live mode creates or allows canonical root `debug/`.
   - The test must fail if live mode writes root `00_*` through `15_*` outside `live/<timestamp>/`.
   - The test must not pass when the live audit subprocess exits non-zero.
   - Prefer a fast isolated unit test around a pure output-routing helper instead of a live subprocess.

2. If needed, factor a small helper from `scripts/audit_today.py`.
   - Keep behavior unchanged.
   - Make output routing testable without sidecar/LLM.

3. Update the report.
   - Write `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/25_rework_08_report.md`.

## Verification

Run and report exact results:

```bash
apps/api/.venv/bin/python -m pytest apps/api/tests/test_astronomy_oracle.py apps/api/tests/test_semantic_contexts.py -q
apps/api/.venv/bin/python -m pytest apps/api/tests/test_astronomy_oracle.py apps/api/tests/test_semantic_contexts.py apps/api/tests/test_today_concrete_advice_consistency.py apps/api/tests/test_today_concrete_advice.py apps/api/tests/test_day_endpoints.py apps/api/tests/test_calendar_endpoints.py -q
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

Commit all intended changes. Do not push/deploy.

When done, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 08 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/25_rework_08_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/23_rework_07_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/24_rework_08_TZ.md. Branch: main. Commit: <HEAD>. Push: NOT_ATTEMPTED"}'
```
