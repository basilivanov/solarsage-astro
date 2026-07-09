# W7 Rework 04 TZ - Fix Venv Symlink Detection

## Context

Read first:

- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/11_rework_03_review.md`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/09_rework_03_TZ.md`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/10_rework_03_report.md`

Work on branch `main`.

Do not push. Do not deploy. Do not use `sudo`.

## Problem

Rework 03 added a re-exec bootstrap, but it compares:

```python
Path(sys.executable).resolve()
Path("apps/api/.venv/bin/python").resolve()
```

On this server both resolve to `/usr/bin/python3.12`, because `apps/api/.venv/bin/python` is a symlink. That makes the script skip re-exec even though it is not running in the venv.

As a result these required commands still fail:

```bash
python3 scripts/check_v2_performance_budgets.py
python3 scripts/check_solarsage_v2_rollout_gates.py
```

## Required Change

Fix venv detection in the gate bootstrap:

1. Detect whether the current process is actually inside `apps/api/.venv`.
2. Do not use resolved binary target equality as the "already in venv" check.
3. If `apps/api/.venv/bin/python` exists and the current process is not in that venv, re-exec through `apps/api/.venv/bin/python`.
4. Preserve all CLI args.
5. Keep a recursion guard.
6. If the venv does not exist, continue with the current interpreter for CI compatibility.
7. Keep the change narrow. Do not change scoring, fixtures, frontend, cache, contracts, or rollout semantics.

Recommended implementation:

```python
api_venv = repo_root / "apps" / "api" / ".venv"
venv_python = api_venv / "bin" / "python"
current_prefix = Path(sys.prefix).resolve()
in_api_venv = current_prefix == api_venv.resolve()
if venv_python.exists() and not in_api_venv and not os.environ.get(RE_EXEC_GUARD):
    env = os.environ.copy()
    env[RE_EXEC_GUARD] = "1"
    os.execve(str(venv_python), [str(venv_python)] + sys.argv, env)
```

You may also account for `VIRTUAL_ENV`, but the important invariant is that system `python3` must not be treated as equivalent just because both executables resolve to the same binary target.

## Verification Required

Run exactly from repo root:

```bash
python3 - <<'PY'
import sys
from pathlib import Path
print(Path(sys.executable).resolve())
print(Path('apps/api/.venv/bin/python').resolve())
print(Path(sys.executable).resolve() == Path('apps/api/.venv/bin/python').resolve())
PY
```

This should still show why the old check was invalid.

Then run:

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

`docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/13_rework_04_report.md`

The report must include:

- changed files
- exact implementation decision for venv detection
- exact verification commands and pass/fail outputs
- commit SHA
- whether push/deploy was attempted; expected: not attempted
- confirmation that no `sudo` was used

## Commit

Commit your changes on `main`.

Include the existing untracked Rework 03 report and the new Rework 04 report in the commit:

- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/10_rework_03_report.md`
- `docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/13_rework_04_report.md`

Suggested message:

```bash
git commit -m "W7 Rework 04: fix venv symlink gate detection"
```

## Callback

At the very end, after report and commit, run:

```bash
HEAD_SHA="$(git rev-parse --short HEAD)"
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d "{\"prompt\":\"Wave W7 Rework 04 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/13_rework_04_report.md. Review: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/11_rework_03_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/12_rework_04_TZ.md. Branch: main. Commit: ${HEAD_SHA}. Push: NOT_ATTEMPTED\"}"
```
