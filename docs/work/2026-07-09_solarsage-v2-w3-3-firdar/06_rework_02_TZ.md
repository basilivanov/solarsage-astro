# W3.3 Rework 02 TZ: Close Fixture and GRACE Contract Gaps

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Close the remaining findings in:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/05_rework_01_review.md
```

Keep this rework narrow:

- do not change accepted Firdar sequences;
- do not change Basil/date boundary results;
- do not add techniques;
- no scoring v2;
- no TodayService wiring;
- no push/deploy.

## Required Changes

### 1. Load activation rules once

In `activation_builder.py`, load `activation_rules.v1.yml` once for both Firdar strength lookups.

Add or adjust a focused test proving:

- one activation-rules load for a request with major+minor;
- missing `firdar_major` or `firdar_minor` still raises `KeyError`.

### 2. Complete Firdar GRACE function contracts

Add `START_FUNCTION_CONTRACT` / `END_FUNCTION_CONTRACT` comments for:

```text
_display_name
_clamp_birthday
_completed_years
_last_birthday
_next_birthday
_age_years_decimal
FirdarContext.__init__
```

Keep existing module/block markers.

Correct module contract text:

- remove unrelated unknown-sign failure wording;
- document actual failures: missing/malformed canon, invalid dates, impossible canon division values;
- do not import `grace_control`.

### 3. Fully compare historical fixture period contracts

For both:

```text
apps/solarsage/tests/fixtures/vasiliy_2026-05-30.json
apps/solarsage/tests/fixtures/test_user_2026-06-15.json
```

Compare the selected canon sequence against every fixture period:

- all nine major lord keys;
- `years`;
- `start_age`;
- `end_age`;
- all `sub_periods[].lord` rotations;
- node-period subperiod order;
- day/night flag.

Use numeric tolerance for floating boundaries.

Do not duplicate expected arrays when the fixture itself is the oracle.

### 4. Document legacy integer-age subperiod limitation

The historical `test_user` fixture contains:

```text
current_sub_period = MARS
```

because the old collector called its Firdaria endpoint with integer age `36`.

The new W3.3 date-precise calculation for `2026-06-15` is:

```text
age_years ~= 36.41369863
current minor = SUN
```

Tests/report must explicitly state:

- fixture `periods` are the compatibility oracle for sequence/boundaries;
- fixture `current_period` may be used where integer/date precision does not change the major;
- fixture `current_sub_period` is not the oracle for date-precise active minor;
- current minor is verified from the period table using the date-precise age.

Update `04_rework_01_report.md` only if needed for factual correction, or describe the correction in the new report.

### 5. Strengthen node endpoint assertions

Add exact endpoint tests for dates at exact ages `70.0` and `73.0`.

Assert:

```text
id = firdar_major__PERIOD_LORD__NORTH_NODE_TRUE
target_key = NORTH_NODE_TRUE
target_planet = NORTH_NODE_TRUE
evidence starts with "North Node is major firdar lord"
by_planet[NORTH_NODE_TRUE] contains the id
```

and equivalent South Node assertions.

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
    --out /tmp/sidecar_activation_w3_3_rework_02_$i.json
  sha256sum /tmp/sidecar_activation_w3_3_rework_02_$i.json
done
cmp -s /tmp/sidecar_activation_w3_3_rework_02_1.json /tmp/sidecar_activation_w3_3_rework_02_2.json
cmp -s /tmp/sidecar_activation_w3_3_rework_02_1.json /tmp/sidecar_activation_w3_3_rework_02_3.json
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
git diff --name-only 30b11c6..HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/07_rework_02_report.md
```

Include:

- changed files;
- single activation-rules load proof;
- completed GRACE function contract list;
- full day/night fixture comparison proof;
- explicit legacy integer-age subperiod note;
- exact North/South Node endpoint proof;
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
  -d '{"prompt":"Wave W3.3 Rework 02 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/07_rework_02_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/05_rework_01_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/06_rework_02_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
