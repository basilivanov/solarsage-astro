# W4 Rework 04 TZ — Robust Audit Runtime Detection

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W4 Rework 03/report
Push/deploy: do not push or deploy.

## Goal

Fix the remaining runtime bootstrap gap from:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/11_rework_03_review.md
```

Do not implement W5. Do not modify `TodayService`, `CalendarService`, frontend, generated contracts, cache keys, feature flags, LLM, semantic layer, sidecar, or scoring semantics.

## Required Fix

File:

```text
scripts/audit_scoring_v2.py
```

Change `_ensure_api_runtime()` so it tests a real API runtime import, not only `import app`.

Required behavior:

- `python3 scripts/audit_scoring_v2.py ...` from repo root still exits 0.
- `PYTHONPATH=/opt/solarsage-astro/apps/api python3 scripts/audit_scoring_v2.py ...` also exits 0 by re-execing into `apps/api/.venv/bin/python`.
- Detection must be based on importing a module that proves API dependencies are valid, for example:

```python
from app.schemas.normalization import AstroSignal
```

or an equivalent API module that requires the real Pydantic 2 runtime.

- Catch broad import/runtime dependency failures enough to re-exec safely. Do not swallow failures after the script is already running under the venv; if the venv runtime itself is broken, fail normally.
- Avoid infinite re-exec loops. A simple guard such as comparing `Path(sys.executable).resolve()` to the venv interpreter path is acceptable.

Keep this local and deterministic:

- no network;
- no DB;
- no Telegram;
- no sidecar;
- no mutation except requested output JSON files.

Update the report only; no need to change W4 scoring code.

## Required Verification

Run and report exact results:

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

Expected final state:

- both audit CLI commands exit 0;
- tracked tree has no modifications/deletions;
- pre-existing untracked files may remain and must be reported separately.

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/13_rework_04_report.md
```

Include:

- changed files;
- exact runtime detection import used;
- both audit CLI verification results;
- V2 targeted test result;
- final `git status --short --branch`;
- commit SHA;
- push status `NOT_ATTEMPTED`.

Commit implementation, artifacts if changed, and report. Do not push or deploy.

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W4 Rework 04 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/13_rework_04_report.md. Review: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/11_rework_03_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/12_rework_04_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
