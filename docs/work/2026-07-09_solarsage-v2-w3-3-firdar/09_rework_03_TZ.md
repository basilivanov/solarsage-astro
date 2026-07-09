# W3.3 Rework 03 TZ: Close Remaining Test/Contract Gaps

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Close the remaining findings in:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/08_rework_02_review.md
```

Keep this rework narrow:

- do not change accepted Firdar day/night sequences;
- do not change Basil/date boundary results;
- do not add techniques;
- no scoring v2;
- no TodayService wiring;
- no push/deploy.

## Required Changes

### 1. Make activation-rules load test exact

Update `apps/solarsage/tests/test_firdar.py::test_activation_rules_loaded_once_firdar`.

Required behavior:

- one request with `techniques=["firdar_major", "firdar_minor"]`;
- spy `_load_activation_rules`;
- assert `load_count == 1` immediately after that request.

If you keep a second request, assert `load_count == 2` after the second request. Do not use `<=`.

### 2. Add exact missing-key tests for Firdar strengths

Add focused tests for these exact cases:

- `period_strengths.firdar_major` missing raises `KeyError`;
- `period_strengths.firdar_minor` missing raises `KeyError`.

Use the smallest reliable surface. Direct `_get_period_strength()` tests with copied/mutated rules are acceptable. An endpoint/build-layer test is also acceptable if it proves the same failure without hiding the exception.

### 3. Fix `firdar.py` module contract and canon failure behavior

In `apps/solarsage/solarsage/services/firdar.py`:

- remove the inaccurate `unknown sign/strength keys` invariant;
- make failure_policy match actual behavior;
- preferred: add explicit canon validation so malformed Firdar canon cannot silently fall back.

Preferred validation:

- `cycle_years > 0`;
- `minor_divisions > 0`;
- selected day/night sequence is non-empty;
- every selected sequence entry has a lord and positive years;
- selected sequence year sum equals `cycle_years` within a small tolerance;
- `node_minor_sequence` length equals `minor_divisions`.

Raise `ValueError` for malformed canon values and keep `KeyError` for missing required keys.

Add tests proving:

- `minor_divisions = 0` raises `ValueError`;
- selected sequence sum mismatch raises `ValueError`;
- node minor sequence length mismatch raises `ValueError`.

If you add a helper, include a GRACE function contract for it.

### 4. Move/complete `FirdarContext.__init__` contract

Move the `START_FUNCTION_CONTRACT` / `END_FUNCTION_CONTRACT` for `FirdarContext.__init__` so it clearly belongs to `def __init__`.

Include:

```text
returns: None
```

Do not import `grace_control`.

## Required Verification

Run and report exact results:

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_firdar.py tests/test_activation_layer_endpoint.py tests/test_activation_transits.py tests/test_activation_schema.py tests/test_profections.py -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_firdar.py tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
python3 scripts/audit_sidecar_activation.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor \
  --out artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
git diff --exit-code -- artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
```

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py \
    --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
    --date 2026-07-08 \
    --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor \
    --out /tmp/sidecar_activation_w3_3_rework_03_$i.json
  sha256sum /tmp/sidecar_activation_w3_3_rework_03_$i.json
done
cmp -s /tmp/sidecar_activation_w3_3_rework_03_1.json /tmp/sidecar_activation_w3_3_rework_03_2.json
cmp -s /tmp/sidecar_activation_w3_3_rework_03_1.json /tmp/sidecar_activation_w3_3_rework_03_3.json
```

```bash
python3 - <<'PY'
import json
from pathlib import Path

p = Path("artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json")
data = json.loads(p.read_text())
assert data["_audit_meta"]["wave"] == "W3.3"
assert len(data["activations"]) == 117
major = next(a for a in data["activations"] if a["id"] == "firdar_major__PERIOD_LORD__SUN")
minor = next(a for a in data["activations"] if a["id"] == "firdar_minor__SUBPERIOD_LORD__SATURN")
assert major["debug"]["age_years"] == 45.68767123
assert major["strength"] == 0.65
assert minor["strength"] == 0.40
print(major["evidence"])
print(minor["evidence"])
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
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/10_rework_03_report.md
```

Include:

- changed files;
- exact single-load proof;
- exact missing-key proof for `firdar_major` and `firdar_minor`;
- module contract/canon validation proof;
- exact verification results;
- artifact/hashseed result;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.3 Rework 03 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/10_rework_03_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/08_rework_02_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/09_rework_03_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
