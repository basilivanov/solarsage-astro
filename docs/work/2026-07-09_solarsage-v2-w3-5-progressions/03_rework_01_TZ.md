# W3.5 Rework 01 TZ — Progression Contract Closure

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Reviewed implementation: `887228c`
Review: `docs/work/2026-07-09_solarsage-v2-w3-5-progressions/02_arch_review.md`
Push/deploy: do not push/deploy.

## Goal

Fix W3.5 without expanding scope.

Do not implement:
- `eclipse_window`
- scoring v2
- convergence
- TodayService sidecar wiring
- semantic/LLM/frontend work
- push/deploy

## Required fixes

### 1. Canon orb lookup

Replace the current generic orb helper with strict per-technique lookup.

Required behavior:
- `solar_arc` context reads `activation_rules.v1.yml -> techniques.solar_arc.orb`.
- `secondary_progression` context reads `activation_rules.v1.yml -> techniques.secondary_progression.orb`.
- missing key raises a loud exception in tests/dev;
- non-numeric value raises a loud exception in tests/dev;
- no hidden fallback orb.

Add tests proving missing `solar_arc.orb` and missing `secondary_progression.orb` fail.

### 2. Canon strength lookup and actual strength formula

The production strength value must be computed from the same canon base stored in debug.

Required formula:

```text
orb_factor = max(0, 1 - orb / max_orb)
strength = round(min(1.0, base_strength * orb_factor), 4)
```

Required bases:
- `solar_arc_aspect`
- `progressed_moon_aspect`
- `progressed_sun_sign_transition`
- `progressed_sun_house_transition`

Do not leave `0.7` or `0.5` as hidden runtime constants.

Add tests:
- missing all four `progression_base` keys fails in the relevant path/helper;
- every W3.5 aspect activation with `debug.orb_factor` has `strength == round(debug.base_strength * debug.orb_factor, 4)`;
- Sun transition strengths use their own canon bases.

### 3. Debug contract

All W3.5 aspect activations must include:
- `source_longitude`
- `target_longitude`
- `angular_distance`
- `aspect_angle`
- `orb`
- `orb_factor`
- `base_strength`

Solar arc aspects must additionally keep:
- `solar_arc_delta`
- `natal_sun_longitude`
- `progressed_sun_longitude`
- `solar_arc_source_longitude`

Sun transitions must include every TZ transition key, using `None` where not applicable:
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

### 4. Sun transition coverage

Add deterministic test coverage for:
- progressed Sun sign transition;
- progressed Sun natal-house transition;
- Aries/Pisces 0-degree wrap-around behavior, or an equivalent direct proof that the boundary logic handles wrap-around correctly.

Basil `2026-07-08` does not need to produce a Sun transition; the test can use a separate fixture/date or direct context.

### 5. Stable solar arc IDs

Use uppercase canonical source keys in solar arc IDs:

```text
solar_arc__MARS__TRINE__NATAL_VENUS
solar_arc__MARS__OPPOSITION__NATAL_ANGLE_ASC
solar_arc__VENUS__SQUARE__NATAL_LOT_NECESSITY
```

Keep evidence display names human-readable, for example `Solar Arc Mars trine natal Venus`.

### 6. Shared aspect canon

Do not duplicate the canonical aspect map/classification in a way that can diverge from `activation_builder.py`.

Acceptable approaches:
- reuse the existing constants/helpers carefully;
- or extract a tiny shared helper and update both callers.

Add a regression proving progression aspect angles match the builder canonical map.

## Artifact

Regenerate:

```text
artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json
```

The regenerated artifact must:
- have `_audit_meta.wave == "W3.5"`;
- contain `solar_arc` and `secondary_progression`;
- contain no `eclipse_window`;
- have uppercase solar arc ID source keys;
- have no W3.5 strength/debug contradictions.

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
    --out /tmp/sidecar_activation_w3_5_rework_01_$i.json
  sha256sum /tmp/sidecar_activation_w3_5_rework_01_$i.json
done
cmp -s /tmp/sidecar_activation_w3_5_rework_01_1.json /tmp/sidecar_activation_w3_5_rework_01_2.json
cmp -s /tmp/sidecar_activation_w3_5_rework_01_1.json /tmp/sidecar_activation_w3_5_rework_01_3.json
```

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("artifacts/audit/2026-07-08/21_sidecar_activation_layer_w3_5_progressions.json")
data = json.loads(p.read_text())
assert data["_audit_meta"]["wave"] == "W3.5"
progressions = [a for a in data["activations"] if a["technique"] in {"solar_arc", "secondary_progression"}]
assert progressions
assert {a["technique"] for a in progressions} == {"solar_arc", "secondary_progression"}
assert not any(a["technique"] == "eclipse_window" for a in data["activations"])

for a in progressions:
    assert a["technique_family"] == "progression"
    debug = a["debug"]
    for key in ("progression_method", "birth_jd", "target_jd", "age_years", "progressed_jd", "progressed_utc_iso", "max_orb", "resolved_house_system"):
        assert key in debug, (a["id"], key)

    if a["kind"] in {"solar_arc_aspect", "progressed_moon_aspect"}:
        for key in ("source_longitude", "target_longitude", "angular_distance", "aspect_angle", "orb", "orb_factor", "base_strength"):
            assert key in debug, (a["id"], key)
        expected = round(min(1.0, float(debug["base_strength"]) * float(debug["orb_factor"])), 4)
        assert a["strength"] == expected, (a["id"], a["strength"], expected)

    if a["technique"] == "solar_arc":
        source = a["id"].split("__")[1]
        assert source == source.upper(), a["id"]

print("progression assertions ok", len(progressions))
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
docs/work/2026-07-09_solarsage-v2-w3-5-progressions/04_rework_01_report.md
```

Include:
- changed files;
- how each architect finding was resolved;
- test outputs;
- audit counts and hashseed SHA values;
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
  -d '{"prompt":"Wave W3.5 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-5-progressions/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
