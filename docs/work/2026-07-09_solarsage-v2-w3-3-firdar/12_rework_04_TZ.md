# W3.3 Rework 04 TZ: Validate Caller-Supplied Firdar Canon

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Close the remaining findings in:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/11_rework_03_review.md
```

Keep this rework narrow:

- do not change accepted Firdar day/night sequences;
- do not change Basil/date boundary results;
- do not add techniques;
- no scoring v2;
- no TodayService wiring;
- no push/deploy.

## Required Changes

### 1. Validate canon inside `calculate_firdar()`

In `apps/solarsage/solarsage/services/firdar.py`, ensure `calculate_firdar()` validates any `canon` it receives before using it.

Required behavior:

- `calculate_firdar(..., canon=bad_with_minor_divisions_0)` raises `ValueError`, not `ZeroDivisionError`;
- `calculate_firdar(..., canon=bad_with_selected_sequence_sum_mismatch)` raises `ValueError`, not silent fallback.

It is acceptable if `_load_firdar_canon()` and `calculate_firdar()` both call `_validate_firdar_canon()`.

### 2. Update tests to prove the public path

Change or add tests in `apps/solarsage/tests/test_firdar.py` so validation is proven through `calculate_firdar(...)`, not only by calling `_validate_firdar_canon()` directly.

Required tests:

- `minor_divisions = 0` through `calculate_firdar()` raises `ValueError`;
- selected day sequence sum mismatch through `calculate_firdar(is_day_birth=True, ...)` raises `ValueError`;
- selected night sequence sum mismatch through `calculate_firdar(is_day_birth=False, ...)` raises `ValueError`;
- node minor sequence length mismatch through `calculate_firdar()` raises `ValueError`.

You may keep direct helper tests if useful, but they are not sufficient by themselves.

### 3. Fix remaining contract text

In `calculate_firdar` function contract, remove the inaccurate `strength keys` wording.

The contract should describe:

- `KeyError` for missing canon keys;
- `ValueError` for malformed canon values;
- normal date-related behavior if relevant.

Also clean the module failure policy if needed so it does not imply an unhandled `ZeroDivisionError` is expected behavior.

### 4. Move `FirdarContext.__init__` contract to a normal position

Move the `START_FUNCTION_CONTRACT` / `END_FUNCTION_CONTRACT` for `FirdarContext.__init__` out of the argument list.

Acceptable positions:

- immediately above `def __init__`, or
- inside the method body immediately after the signature.

Keep `returns: None`.

### 5. Remove unused imports

Remove:

- unused `import math` in `_validate_firdar_canon()`;
- unused `_load_firdar_canon` import inside `_validate_canon_test()` if that helper remains.

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
    --out /tmp/sidecar_activation_w3_3_rework_04_$i.json
  sha256sum /tmp/sidecar_activation_w3_3_rework_04_$i.json
done
cmp -s /tmp/sidecar_activation_w3_3_rework_04_1.json /tmp/sidecar_activation_w3_3_rework_04_2.json
cmp -s /tmp/sidecar_activation_w3_3_rework_04_1.json /tmp/sidecar_activation_w3_3_rework_04_3.json
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
rg -n 'strength keys|unknown sign|import math|load_count <=' apps/solarsage/solarsage/services/firdar.py apps/solarsage/tests/test_firdar.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

The `rg` command above should return no matches.

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/13_rework_04_report.md
```

Include:

- changed files;
- proof that `calculate_firdar(canon=bad)` now raises `ValueError`;
- contract cleanup proof;
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
  -d '{"prompt":"Wave W3.3 Rework 04 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/13_rework_04_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/11_rework_03_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/12_rework_04_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
