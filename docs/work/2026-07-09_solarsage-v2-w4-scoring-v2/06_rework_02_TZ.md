# W4 Rework 02 TZ — Clean Artifacts And Strict Canon Completion

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W4 Rework 01/report
Push/deploy: do not push or deploy.

## Goal

Finish the remaining W4 acceptance gaps from:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/05_rework_01_review.md
```

Do not implement W5. Do not modify `TodayService`, `CalendarService`, frontend, generated contracts, cache keys, flags, LLM, semantic layer, or sidecar.

## Required Fixes

### 1. Commit both required W4 audit artifacts and leave tracked tree clean

Regenerate and commit both:

```text
artifacts/audit/2026-07-08/22_scoring_v2_result.json
artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

Current state after Rework 01 callback has `23_scoring_v2_diff.json` dirty. That is not acceptable.

After all tests and artifact generation, `git status --short --branch` must show no tracked modifications or deletions. Pre-existing untracked local files may remain; report them separately.

### 2. Remove remaining hidden runtime fallbacks for required canon values

File:

```text
apps/api/app/services/scoring_v2_service.py
```

Replace all remaining required W4 scoring `.get(..., fallback_constant)` lookups with strict lookups:

- convergence curve value for `capped_n`;
- `dominance_cap.enabled`;
- activation polarity sphere amount modifier for the activation polarity;
- activation status support modifier for the activation polarity;
- activation status tension modifier for the activation polarity;
- debug dominance cap `enabled`;
- any other W4 scoring config value from `scoring_v2.v1.yml` or `activation_rules.v1.yml` currently using a silent fallback.

Concrete examples to fix:

```text
curve.get(capped_n, 0.0)
cap_config.get("enabled", True)
support_mod.get(pol, 0.0)
tension_mod.get(pol, 0.0)
polarity_mod.get(act.polarity or "neutral", 1.0)
```

Also change `_family_for_technique()` to use strict `technique_families` lookup, not `rules.get("technique_families", {})`.

If a required canon key is missing, raise `KeyError` or `ValueError`. Do not silently alter scoring semantics.

Add or update tests proving:

1. Missing `activation_polarity.sphere_amount_modifier.neutral` raises.
2. Missing `activation_polarity.status_support_modifier.neutral` or `status_tension_modifier.neutral` raises.
3. Missing `convergence_curve[3]` raises for a three-family convergence fixture.

Tests may monkeypatch `app.services.scoring_v2_service._SCORING_V2` with a deep-copied config and must restore it.

### 3. Remove dead module state

Remove the unused:

```python
_ACTIVE_ACTIVATIONS
```

W4 must remain a pure service without unused module-level mutable state.

## Required Verification

Run and report exact results:

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

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

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
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from copy import deepcopy
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service
import app.services.scoring_v2_service as svc

orig = deepcopy(svc._get_scoring_v2())

def layer_for(polarity: str = "neutral") -> ActivationLayer:
    return ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[ActivationEvidence(
            id="canon_missing_key",
            technique="annual_profection",
            technique_family="profection",
            target_type="planet",
            target_key="MERCURY",
            kind="lord",
            phase="period",
            strength=1.0,
            polarity=polarity,
            evidence="strict canon check",
        )],
        by_planet={"MERCURY": ["canon_missing_key"]},
        by_house={},
        by_lot={},
        by_angle={},
    )

for section in ("sphere_amount_modifier", "status_support_modifier", "status_tension_modifier"):
    mut = deepcopy(orig)
    del mut["activation_polarity"][section]["neutral"]
    svc._SCORING_V2 = mut
    try:
        ScoringV2Service().score_day([], layer_for("neutral"))
        raise AssertionError(f"missing {section}.neutral did not raise")
    except KeyError:
        pass

mut = deepcopy(orig)
del mut["convergence_curve"][3]
svc._SCORING_V2 = mut
try:
    acts = [
        ActivationEvidence(id="p", technique="annual_profection", technique_family="profection", target_type="planet", target_key="MERCURY", kind="lord", phase="period", strength=0.1, polarity="supportive", evidence="p"),
        ActivationEvidence(id="t", technique="transit_to_natal", technique_family="transit", target_type="planet", target_key="MERCURY", kind="trine", phase="period", strength=0.1, polarity="supportive", evidence="t"),
        ActivationEvidence(id="f", technique="firdar_major", technique_family="firdar", target_type="planet", target_key="MERCURY", kind="lord", phase="period", strength=0.1, polarity="supportive", evidence="f"),
    ]
    layer = ActivationLayer(calculation_version="1", target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow", house_system="WHOLE_SIGN", activations=acts, by_planet={"MERCURY": ["p", "t", "f"]}, by_house={}, by_lot={}, by_angle={})
    ScoringV2Service().score_day([], layer)
    raise AssertionError("missing convergence_curve[3] did not raise")
except KeyError:
    pass
finally:
    svc._SCORING_V2 = orig

print("strict canon missing-key checks passed")
PY
```

```bash
rg -n '_ACTIVE_ACTIVATIONS|\\.get\\([^\\n]*(0\\.0|1\\.0|0\\.65|1\\.3|0\\.8|0\\.7|True)|curve\\.get|polarity_mod\\.get|support_mod\\.get|tension_mod\\.get|rules\\.get\\(\"technique_families\"' apps/api/app/services/scoring_v2_service.py
```

Expected: no matches for W4 runtime fallback patterns.

```bash
rg -n 'ss-scoring-2.0' apps/api/app/services/today_service.py artifacts/audit/2026-07-08/11_final_today_payload.json || true
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Expected runtime proof:

```text
No `ss-scoring-2.0` references in TodayService or final TodayPayload.
```

Expected final working tree:

```text
No tracked-file modifications/deletions.
```

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/07_rework_02_report.md
```

Include:

- changed files;
- proof both W4 artifacts are committed;
- strict missing-key test coverage;
- exact verification command results;
- `rg` proof no fallback patterns remain in `scoring_v2_service.py`;
- runtime `/day` remains V1 proof;
- final `git status --short --branch`;
- commit SHA;
- push status `NOT_ATTEMPTED`.

Commit implementation, both artifacts, and report. Do not push or deploy.

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W4 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
