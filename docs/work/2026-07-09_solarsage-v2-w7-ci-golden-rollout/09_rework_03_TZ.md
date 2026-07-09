# W7 Rework 03 TZ - Interpreter-Portable Golden Gates

## Context

Read first:

- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/08_rework_02_review.md`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/06_rework_02_TZ.md`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/07_rework_02_report.md`

Work on branch `main`.

Do not push. Do not deploy. Do not use `sudo`.

## Problem

W7 Rework 02 is architecturally close, but the required direct gates fail when run exactly as an operator would run them from repo root:

```bash
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
```

Both currently fail outside the API venv with:

```text
ModuleNotFoundError: No module named 'pydantic.alias_generators'
```

## Required Change

Make the W7 gate scripts interpreter-portable:

1. `python3 scripts/check_v2_performance_budgets.py` must pass from repo root on this server.
2. `python3 scripts/check_solarsage_v2_rollout_gates.py` must pass from repo root on this server.
3. CI must still work in an environment where dependencies are installed into the current interpreter and `apps/api/.venv` may not exist.
4. Keep the change narrow. Do not change scoring semantics, fixtures, frontend behavior, cache logic, or API contracts.

Preferred implementation:

- In `scripts/check_v2_performance_budgets.py`, before importing API modules, detect repo root and `apps/api/.venv/bin/python`.
- If that venv Python exists and `sys.executable` is not already that path, re-exec the script through it.
- Use a recursion guard environment variable so this cannot loop forever.
- Preserve all CLI arguments.
- If the venv does not exist, continue with current `sys.executable`; this is the CI path after `pip install -e apps/api`.
- `scripts/check_solarsage_v2_rollout_gates.py` may rely on this self-reexec or may resolve and call the same interpreter explicitly. Choose the simpler robust option.

## Verification Required

Run exactly:

```bash
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
python3 scripts/check_audit_golden.py
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_golden_basil_2026_07_08.py tests/test_golden_v2_convergence.py tests/test_v2_performance_budgets.py -q
```

Then from repo root run:

```bash
rg -n '/opt/solarsage-astro|833478509|basil_ivanov|1980-10-30|Мончегорск|67\.9394|32\.8144|43\.59699|39\.72477' apps/api/tests/fixtures/golden apps/api/tests/test_golden_basil_2026_07_08.py scripts/check_audit_golden.py scripts/check_v2_performance_budgets.py scripts/check_solarsage_v2_rollout_gates.py
rg -n 'birth_local_date|progressed_utc_iso|raw_natal_context|raw_activations|source_longitude|target_longitude' apps/api/tests/fixtures/golden
python3 scripts/check_logging_guardrails.py
git show --check HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git status --short --branch
```

For both `rg` privacy scans, no matches is the expected passing result.

## Report Required

Write:

`docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/10_rework_03_report.md`

The report must include:

- changed files
- exact implementation decision for interpreter portability
- exact verification commands and pass/fail outputs
- commit SHA
- whether push/deploy was attempted; expected: not attempted

## Commit

Commit your changes on `main`.

Suggested message:

```bash
git commit -m "W7 Rework 03: make golden gates interpreter portable"
```

## Callback

At the very end, after report and commit, run:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W7 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/09_rework_03_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
