# W3.5 Rework 02 TZ — Finish Transition Contract and Artifact Commit

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Reviewed commit: `e899a8a`
Review: `docs/work/2026-07-09_solarsage-v2-w3-5-progressions/05_rework_01_review.md`
Push/deploy: do not push/deploy.

## Goal

Close the remaining W3.5 Rework 01 gaps without changing scope.

Do not implement:
- `eclipse_window`
- scoring v2
- convergence
- TodayService sidecar wiring
- semantic/LLM/frontend work
- push/deploy

## Required fixes

### 1. Commit the regenerated W3.5 artifact

The current working tree has:

```text
M artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json
```

This artifact must be included in the rework commit. It contains required contract changes:
- uppercase solar arc source IDs;
- solar arc `source_longitude`;
- corrected secondary progression strengths.

Do not leave the working tree dirty after callback, except pre-existing unrelated untracked files.

### 2. Pass through full Sun transition debug in `ActivationEvidence`

Update `apps/solarsage/solarsage/services/activation_builder.py`.

For sign transition activations, final `debug` must include:
- `transition_type`
- `current_sign`
- `previous_sign`
- `next_sign`
- `current_house`
- `target_house`
- `boundary_longitude`
- `distance_to_boundary`
- `base_strength`
- `orb_factor`

For house transition activations, final `debug` must include the same key set, with `None` for non-applicable sign/house fields.

The data is already present in the transition dict returned by `progressed_sun_transitions()`; do not recompute it in the builder.

### 3. Make Sun transition tests deterministic

Replace conditional transition tests with deterministic tests that fail if the transition is absent.

Required coverage:
- helper-level sign transition;
- helper-level house transition;
- wrap-around at Pisces/Aries boundary;
- builder/endpoint-level final `ActivationEvidence.debug` for sign transition;
- builder/endpoint-level final `ActivationEvidence.debug` for house transition.

Recommended approach:
- For helper tests, use a minimal fake context object with `progressed_sun_lon`, `birth_jd`, and `max_orb`, and monkeypatch `calculate_houses_cusps()` for house-cusp checks.
- For builder tests, monkeypatch `solarsage.services.progressions.calculate_secondary_progression_context`, `progressed_moon_aspects`, and `progressed_sun_transitions` so `build_activation_layer(... techniques=["secondary_progression"])` returns deterministic transition activations. Then assert final debug keys and strength formula.

Do not use tests that pass when the transition list is empty.

### 4. Remove aspect canon duplication

Do one of:
- extract `ASPECT_ANGLES` and `_classify_polarity()` into a small shared module and use it from both `activation_builder.py` and `progressions.py`;
- or make `progressions.py` import/reuse the builder constants/helpers in a way that does not create runtime circular-import problems.

Keep or update `test_progression_aspects_match_builder_map` so it proves both paths use the same aspect canon.

### 5. Add non-numeric orb tests

Add a parametrized regression that both:
- `solar_arc.orb = "bad"`
- `secondary_progression.orb = "bad"`

fail loudly.

Use `KeyError` or `ValueError`, but be consistent with implementation and report it honestly.

## Verification

Run and include exact outputs in the report:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_solar_arc.py \
  tests/test_secondary_progressions.py \
  tests/test_activation_layer_endpoint.py \
  tests/test_firdar.py \
  tests/test_profections.py \
  tests/test_activation_transits.py \
  tests/test_activation_schema.py -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_activation_layer_progressions.py \
  tests/test_activation_layer_returns.py \
  tests/test_activation_layer_firdar.py \
  tests/test_activation_layer_profections.py \
  tests/test_activation_layer_transits.py \
  tests/test_activation_layer_contract.py \
  tests/test_today_meta_versions.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
python3 scripts/audit_sidecar_activation.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor,solar_return,lunar_return,solar_arc,secondary_progression \
  --out artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json
```

```bash
set -e
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py \
    --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
    --date 2026-07-08 \
    --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor,solar_return,lunar_return,solar_arc,secondary_progression \
    --out /tmp/sidecar_activation_w3_5_rework_02_$i.json
  sha256sum /tmp/sidecar_activation_w3_5_rework_02_$i.json
done
cmp -s /tmp/sidecar_activation_w3_5_rework_02_1.json /tmp/sidecar_activation_w3_5_rework_02_2.json
cmp -s /tmp/sidecar_activation_w3_5_rework_02_1.json /tmp/sidecar_activation_w3_5_rework_02_3.json
```

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json")
data = json.loads(p.read_text())
progressions = [a for a in data["activations"] if a["technique"] in {"solar_arc", "secondary_progression"}]
assert data["_audit_meta"]["wave"] == "W3.5"
assert progressions
assert {a["technique"] for a in progressions} == {"solar_arc", "secondary_progression"}
assert not any(a["technique"] == "eclipse_window" for a in data["activations"])

for a in progressions:
    if a["kind"] in {"solar_arc_aspect", "progressed_moon_aspect"}:
        debug = a["debug"]
        for key in ("source_longitude", "target_longitude", "angular_distance", "aspect_angle", "orb", "orb_factor", "base_strength"):
            assert key in debug, (a["id"], key)
        expected = round(min(1.0, float(debug["base_strength"]) * float(debug["orb_factor"])), 4)
        assert a["strength"] == expected, (a["id"], a["strength"], expected)
    if a["technique"] == "solar_arc":
        source = a["id"].split("__")[1]
        assert source == source.upper(), a["id"]
print("artifact ok", len(progressions))
PY
```

```bash
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-5-progressions/07_rework_02_report.md
```

Include:
- changed files;
- how each Rework 02 finding was resolved;
- test outputs;
- audit counts and hashseed SHA values;
- proof that the artifact is committed;
- proof that `TodayService` is still unwired;
- commit SHA;
- push status `NOT_ATTEMPTED`.

Commit the rework and report. Do not push or deploy.

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.5 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
