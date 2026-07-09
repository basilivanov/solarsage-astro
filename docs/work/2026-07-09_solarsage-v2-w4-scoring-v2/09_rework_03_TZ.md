# W4 Rework 03 TZ — Audit CLI Runs From Repo Root

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W4 Rework 02/report
Push/deploy: do not push or deploy.

## Goal

Fix the last W4 acceptance gap from:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/08_rework_02_review.md
```

The documented W4 command must run from repo root:

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

Do not implement W5. Do not modify `TodayService`, `CalendarService`, frontend, generated contracts, cache keys, feature flags, LLM, semantic layer, or sidecar.

## Required Fix

File:

```text
scripts/audit_scoring_v2.py
```

Make the script runnable from a clean repo-root shell via the exact documented command above.

Context:

- `/usr/bin/python3` currently has Pydantic 1 and no `app` import path.
- `apps/api/.venv/bin/python scripts/audit_scoring_v2.py ...` works.
- The API venv is the canonical backend runtime for this repo.

Preferred implementation:

1. At the top of `scripts/audit_scoring_v2.py`, before importing `app.*`, detect whether the current interpreter can import the API runtime correctly.
2. If not, re-exec the script under:

```text
apps/api/.venv/bin/python
```

using the same script path and CLI arguments.

3. If the API venv interpreter is missing, fail fast with a clear stderr message telling the operator to create/use the API venv.

Keep this deterministic and local:

- no network;
- no DB;
- no Telegram;
- no sidecar;
- no mutation except the requested output JSON files.

Update the GRACE module contract in the script to mention the possible local re-exec into the API venv. This is a local process bootstrap, not an external service call.

Do not hide scoring semantics or add scoring fallbacks.

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
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
import json
from pathlib import Path
from app.schemas.scoring_v2 import ScoringV2Result

result = json.loads(Path("artifacts/audit/2026-07-08/22_scoring_v2_result.json").read_text())
diff = json.loads(Path("artifacts/audit/2026-07-08/23_scoring_v2_diff.json").read_text())

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
rg -n '_ACTIVE_ACTIVATIONS|\.get\([^\n]*(0\.0|1\.0|0\.65|1\.3|0\.8|0\.7|True)|curve\.get|polarity_mod\.get|support_mod\.get|tension_mod\.get|rules\.get\("technique_families"' apps/api/app/services/scoring_v2_service.py || true
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Expected:

- documented `python3 scripts/audit_scoring_v2.py ...` command exits 0;
- regenerated artifacts remain committed and deterministic;
- no tracked-file modifications/deletions after all verification commands;
- no W4 runtime fallback pattern matches in `scoring_v2_service.py`;
- no `ss-scoring-2.0` references in `TodayService` or final TodayPayload.

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/10_rework_03_report.md
```

Include:

- changed files;
- exact bootstrap behavior;
- exact verification command results;
- proof artifact regeneration via `python3 scripts/audit_scoring_v2.py ...`;
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
  -d '{"prompt":"Wave W4 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/09_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
