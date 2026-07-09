# W4 Architect Acceptance — Scoring V2 Pure Service

Status: ACCEPTED
Branch: main
Push/deploy: NOT_ATTEMPTED

## Accepted Scope

W4 is accepted as an offline/pure Scoring V2 layer:

- `ScoringV2Service` and contracts exist behind explicit API/service calls.
- W4 audit artifacts are reproducible from the documented repo-root CLI.
- Activation-layer scoring, convergence bonus, anti-dominance, thresholding, family dedup, and breakdown contract are covered by targeted tests.
- Runtime `/day` and calendar wiring remain out of scope for W4 and must be handled in W5.

Accepted commits:

- `d16f636` — W4 TZ
- `1be2c76` / `29e4cb7` — initial W4 implementation and report
- `6c777da` / `4e98d97` — rework 01
- `d374cc4` / `3c27b80` — rework 02
- `97d7e14` / `bd1481f` — rework 03
- `e45899e` / `4986823` — rework 04
- `2b52dac` / `3fcb1fd` — rework 05

## Architect Verification

Fresh commands run from `/opt/solarsage-astro` on 2026-07-09.

### Audit CLI from repo root

```bash
python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result artifacts/audit/2026-07-08/22_scoring_v2_result.json \
  --out-diff artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

Result: exit 0.

Output summary:

- `V1 status: supportive`
- `V2 status: steady`
- `Spheres: 9`

### Audit CLI with system `PYTHONPATH`

The first run hit stale `/tmp` files owned by another user. After removing only these two temporary files, the required command passed:

```bash
rm -f /tmp/22_scoring_v2_result_py_path_system.json /tmp/23_scoring_v2_diff_py_path_system.json
PYTHONPATH=/opt/solarsage-astro/apps/api python3 scripts/audit_scoring_v2.py \
  --signals artifacts/audit/2026-07-08/04_day_scored_signals_after_filter.csv \
  --activation-layer artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json \
  --out-result /tmp/22_scoring_v2_result_py_path_system.json \
  --out-diff /tmp/23_scoring_v2_diff_py_path_system.json
```

Result: exit 0.

Output summary:

- `V1 status: supportive`
- `V2 status: steady`
- `Spheres: 9`

### Artifact validation

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

Result: exit 0, `W4 artifact validation passed`.

### Targeted W4 tests

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

Result: `22 passed in 0.60s`.

### Activation/meta regression

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_layer_contract.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_returns.py \
  tests/test_activation_layer_progressions.py \
  tests/test_activation_layer_eclipse.py \
  tests/test_today_meta_versions.py -q
```

Result: `38 passed in 0.52s`.

### Full backend suite

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

Result: `723 passed, 5 skipped, 1 warning in 53.96s`.

### Static/repo checks

```bash
rg -n '_ACTIVE_ACTIVATIONS|\.get\([^\n]*(0\.0|1\.0|0\.65|1\.3|0\.8|0\.7|True)|curve\.get|polarity_mod\.get|support_mod\.get|tension_mod\.get|rules\.get\("technique_families"' apps/api/app/services/scoring_v2_service.py || true
```

Result: no forbidden fallback matches.

```bash
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
```

Result: no runtime `/day` V2 wiring detected, which is correct for W4 and reserved for W5.

```bash
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Result:

- whitespace checks passed;
- tracked tree stayed clean after artifact generation;
- only pre-existing untracked paths remain: `.grace/`, `docs/superpowers/plans/2026-07-05-fix-day-route-auth-build.md`, `grace.db`, `skills/`.

## Acceptance Notes

The W4 CLI bootstrap defect is fixed at the root cause: `scripts/audit_scoring_v2.py` now executes the unresolved `apps/api/.venv/bin/python` entry path and uses `sys.prefix` as the loop guard, so the venv sees its `pyvenv.cfg` and imports Pydantic 2.

No push/deploy was attempted. Next architectural step is W5: integrate Scoring V2 into runtime `/day` and calendar behind explicit flags/contracts/cache-version gates.
