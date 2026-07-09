# W4 Rework 05 TZ — Preserve Venv Exec Path

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W4 Rework 04/report
Push/deploy: do not push or deploy.

## Goal

Fix the audit bootstrap defect from:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/14_rework_04_review.md
```

Do not modify W4 scoring semantics or any W5/runtime/frontend files.

## Required Fix

File:

```text
scripts/audit_scoring_v2.py
```

### Preserve the venv entry path

Build an absolute venv path, but do not resolve the final symlink before `os.execve()`:

```python
api_root = Path(__file__).resolve().parent.parent / "apps" / "api"
venv_root = api_root / ".venv"
venv_python = venv_root / "bin" / "python"
```

Use:

```python
os.execve(str(venv_python), [str(venv_python), *sys.argv], env)
```

Do not pass `/usr/bin/python3.12` to `execve`.

### Robust loop guard

Use the actual runtime prefix to detect whether the process is already in the API venv:

```python
in_api_venv = Path(sys.prefix).resolve() == venv_root.resolve()
```

Required behavior:

1. Try importing a real API module.
2. If import succeeds, continue.
3. If import fails outside the API venv and no re-exec was attempted, execute the venv entry path.
4. If import fails while already in the API venv, or after the re-exec guard is set, re-raise the original import error instead of looping or silently continuing.
5. If the venv entry path is missing, print a clear stderr error and exit non-zero.

Do not catch and hide a broken API venv.

## Required Verification

Run and report:

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result /tmp/22_scoring_v2_result_py_path_system.json \
  --out-diff /tmp/23_scoring_v2_diff_py_path_system.json
```

Both commands must exit 0.

Verify output:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from app.schemas.scoring_v2 import ScoringV2Result

for result_path, diff_path in [
    ("artifacts/audit/2026-07-08/22_scoring_v2_result.json", "artifacts/audit/2026-07-08/23_scoring_v2_diff.json"),
    ("/tmp/22_scoring_v2_result_py_path_system.json", "/tmp/23_scoring_v2_diff_py_path_system.json"),
]:
    result = json.loads(Path(result_path).read_text())
    diff = json.loads(Path(diff_path).read_text())
    assert result["scoring_version"] == "ss-scoring-2.0"
    assert "scoringVersion" not in result
    ScoringV2Result.model_validate(result)
    assert result["sphere_scores"]
    assert any(v["activation_score"] > 0 for v in result["sphere_scores"].values())
    assert any(v["convergence_bonus"] > 0 for v in result["sphere_scores"].values())
    assert "sphere_diffs" in diff and diff["sphere_diffs"]
print("W4 artifact validation passed")
PY
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_basil_2026_07_08_v2_golden.py -q
```

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Expected:

- both CLI commands exit 0;
- targeted W4 tests pass;
- tracked tree remains clean after artifact generation.

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/16_rework_05_report.md
```

Include changed files, exact CLI results, targeted test result, final git status, commit SHA, and `Push: NOT_ATTEMPTED`.

Commit implementation, artifacts if changed, and report. Do not push or deploy.

## Callback

After implementation, verification, report, and commit:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W4 Rework 05 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/16_rework_05_report.md. Review: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/14_rework_04_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/15_rework_05_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
