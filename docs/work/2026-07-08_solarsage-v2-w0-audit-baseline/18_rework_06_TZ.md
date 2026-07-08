# Wave W0 Rework 06 TZ

You are the coder agent. Work in `/opt/solarsage-astro` on branch `main`.

Read first:
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/17_rework_05_review.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/15_rework_05_TZ.md`
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/16_rework_05_report.md`

Do not push or deploy.

## Goal

Make W0 audit baseline actually safe:

1. Default `make audit-day` must not call live LLM generation or mutate caches to create canonical root artifacts.
2. Missing/invalid committed baseline fixture must fail fast before canonical writes.
3. `--live-llm-sample` must write only under `artifacts/audit/<DATE>/live/<timestamp>/`.
4. Required regression tests must exist.

## Required Architecture

### 1. Split output routing

Refactor `scripts/audit_today.py` so there are two explicit modes:

- **canonical mode**:
  - root output: `artifacts/audit/<DATE>/`
  - debug output: `artifacts/audit/<DATE>/debug/`
  - writes canonical `00_*` through `15_*`

- **live sample mode**:
  - root output: `artifacts/audit/<DATE>/live/<timestamp>/`
  - debug output: `artifacts/audit/<DATE>/live/<timestamp>/debug/`
  - writes all live files only inside that live directory
  - writes no canonical root files and no canonical `debug/*`

Do not implement this by narrowing `git diff` checks. The code path itself must not write canonical paths in live mode.

### 2. Make default canonical mode LLM-free

In default mode:

- Load and validate `artifacts/audit/<DATE>/11_final_today_payload.json` before calling anything that can generate LLM text.
- If that baseline fixture is missing or invalid, exit non-zero before writing canonical files.
- Do not call `TodayService.get_today_payload` in default mode unless you have created a guaranteed no-LLM/no-cache-mutation method and tests prove it cannot generate.
- Build canonical `11_final_today_payload.json` as a deterministic projection:
  - recompute deterministic production inputs: profile, natal context, transits, normalized signals, day-scored signals, scoring, semantic layer, why contexts, oracle comparisons;
  - start from the committed baseline payload for volatile narrative fields;
  - replace deterministic fields from the fresh recomputation where applicable (`meta`, `day_status`, day facts, top flags, concrete advice keys/verdicts/evidence/counts, chart deterministic positions/aspects if available);
  - keep volatile LLM prose frozen from the baseline.

If full projection is too risky in this rework, implement fail-fast default mode that verifies the existing committed baseline and deterministic artifacts without calling LLM. Do not silently refresh the baseline.

### 3. Keep live sample explicitly opt-in

In `--live-llm-sample` mode:

- It is allowed to invalidate/regenerate and call live LLM.
- It must write all outputs only under `live/<timestamp>/`.
- It must not overwrite canonical `00_*` through `15_*`, canonical `debug/*`, or any root canonical file.
- Leave live output untracked or ignored unless explicitly promoted later.

### 4. Add regression tests

Add targeted automated tests. Keep them fast and isolated; do not require a real sidecar or live LLM.

Minimum coverage:

- default mode with missing baseline fixture fails before canonical writes and before any TodayService/LLM generation path;
- live output routing writes only under `live/<timestamp>/` and does not touch canonical root/debug paths;
- supportive `SemanticService.build_why_contexts(...)` with `relationships_partnership` below avoid threshold does not emit the relationship outreach practical bullet.

It is acceptable to factor small pure helpers out of `scripts/audit_today.py` to make this testable.

### 5. Verification

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
rg -n 'Moon Phase Fact: "N/A"|Top Flags: N/A|\| N/A \| N/A \| N/A \||Рекомендация временно недоступна\.|Общайся с близкими.*отнош' artifacts/audit/2026-07-08/14_claims_audit.md artifacts/audit/2026-07-08/11_final_today_payload.json
git diff 2f9173f..HEAD --check
git show --check HEAD
git status --short --branch
```

Expected:
- all pytest/script commands pass;
- both `git diff --exit-code -- artifacts/audit/2026-07-08` checks pass without restoring files;
- the `rg` command returns no matches;
- only known unrelated untracked files remain (`.grace/`, `grace.db`, `skills/`, `docs/superpowers/...`) unless you add a `.gitignore` entry for live audit output.

## Report

Write:
- `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/19_rework_06_report.md`

Include:
- changed files;
- architecture decisions;
- exact verification outputs;
- commit SHA;
- push/deploy status.

Commit all intended changes. Do not push/deploy.

When done, run:

```bash
curl --max-time 10 -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W0 Rework 06 ready for architect review. Report: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/19_rework_06_report.md. Review: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/17_rework_05_review.md. Rework TZ: docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/18_rework_06_TZ.md. Branch: main. Commit: <HEAD>. Push: NOT_ATTEMPTED"}'
```
