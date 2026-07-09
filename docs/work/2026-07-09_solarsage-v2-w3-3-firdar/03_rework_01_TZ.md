# W3.3 Rework 01 TZ: Correct Firdar Boundaries and Contract Discipline

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Resolve every finding in:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/02_arch_review.md
```

Keep scope narrow:

- W3.3 Firdar only;
- no returns/progressions/eclipses;
- no scoring v2;
- no TodayService sidecar wiring;
- no push/deploy.

## Required Fixes

### 1. Fix decimal age denominator

Replace calendar-year denominator logic with the actual birthday interval:

```python
last_birthday = birthday_on_or_before(target_local)
next_birthday = next_birthday_after(last_birthday)
elapsed_days = (target_local - last_birthday).days
interval_days = (next_birthday - last_birthday).days
age_years = completed_years + elapsed_days / interval_days
```

Birthday construction must use one explicit helper with deterministic February 29 clamping.

Required regression:

```text
birth 1990-07-01
target 2000-06-30
day birth

age_years < 10.0
major = SUN
```

And:

```text
birth 1990-07-01
target 2000-07-01
day birth

age_years == 10.0
major = VENUS
minor = VENUS
```

### 2. Support February 29 births

Define and document this rule:

```text
For a February 29 birth, the anniversary in a non-leap year is February 28.
```

Use that rule consistently for last/next birthday.

Add tests covering:

- non-leap target year before clamped anniversary;
- exact clamped anniversary;
- leap target year exact February 29 anniversary;
- no exception.

### 3. Remove Firdar strength fallbacks

Replace:

```python
period_base.get("firdar_major", 0.65)
period_base.get("firdar_minor", 0.40)
```

with strict canon lookup, preferably existing:

```python
_get_period_strength(activation_rules, "firdar_major")
_get_period_strength(activation_rules, "firdar_minor")
```

Add a test proving a missing key raises clearly.

### 4. Compute Firdar context once

When both `firdar_major` and `firdar_minor` are active:

- load Firdar canon once;
- calculate Firdar context once;
- load activation strengths once;
- emit major/minor activations according to requested techniques.

Do not recompute in each loop iteration.

Add a focused monkeypatch/spy test proving `calculate_firdar()` is called once for a request containing both techniques.

### 5. Complete GRACE contracts

Update:

```text
apps/solarsage/solarsage/services/firdar.py
```

Required per `AGENTS.md`:

- complete `AI_HEADER` and `ROLE`;
- `START_MODULE_CONTRACT` / `END_MODULE_CONTRACT`;
- `START_MODULE_MAP` / `END_MODULE_MAP`;
- `START_FUNCTION_CONTRACT` for non-trivial public/internal calculation functions;
- semantic `START_BLOCK` / `END_BLOCK` markers.

Do not import `grace_control`.

Also update the stale top-level role/header in `activation_builder.py` so it no longer claims the module is W3.1 transit-only after W3.2/W3.3 additions. Keep this documentation-only; do not refactor unrelated builder code.

### 6. Add executable node-period coverage

Add service and endpoint tests:

```text
age 70.0 => NORTH_NODE_TRUE major
age 73.0 => SOUTH_NODE major
minor at each exact node-period start => SATURN
```

Assertions:

- target key and target planet use canonical uppercase ids;
- stable activation ids;
- valid `by_planet` references;
- evidence uses readable names:
  - `North Node`
  - `South Node`
- no raw `NORTH_NODE_TRUE`/`SOUTH_NODE` appears in evidence text.

Add display-name mappings without changing canonical target keys.

### 7. Make historical fixture compatibility executable

In sidecar tests, load:

```text
apps/solarsage/tests/fixtures/test_user_2026-06-15.json
apps/solarsage/tests/fixtures/vasiliy_2026-05-30.json
```

Compare canon against:

```text
raw.firdaria.value.is_day_birth
raw.firdaria.value.periods
```

At minimum verify:

- major lord sequence;
- major years/start/end ages;
- each seven-planet subperiod lord order;
- node minor sequence;
- day/night fixture chooses the expected canon sequence.

Do not merely duplicate the fixture values as new hardcoded arrays.

### 8. Regenerate W3.3 artifact only

Regenerate:

```text
artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
```

Do not mutate accepted W3.1/W3.2 artifacts.

Required W3.3 artifact values remain:

```text
wave = W3.3
activation count = 117
major = SUN
minor = SATURN
age_years = 45.68767123
```

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
    --out /tmp/sidecar_activation_w3_3_rework_$i.json
  sha256sum /tmp/sidecar_activation_w3_3_rework_$i.json
done
cmp -s /tmp/sidecar_activation_w3_3_rework_1.json /tmp/sidecar_activation_w3_3_rework_2.json
cmp -s /tmp/sidecar_activation_w3_3_rework_1.json /tmp/sidecar_activation_w3_3_rework_3.json
```

```bash
cd apps/solarsage && venv/bin/python - <<'PY'
from datetime import date
from solarsage.services.firdar import calculate_firdar, _load_firdar_canon

canon = _load_firdar_canon()

before = calculate_firdar(
    birth_local=date(1990, 7, 1),
    target_local=date(2000, 6, 30),
    is_day_birth=True,
    sun_house=9,
    canon=canon,
)
boundary = calculate_firdar(
    birth_local=date(1990, 7, 1),
    target_local=date(2000, 7, 1),
    is_day_birth=True,
    sun_house=9,
    canon=canon,
)

print(before.age_years, before.major_lord, before.minor_lord)
print(boundary.age_years, boundary.major_lord, boundary.minor_lord)

assert before.age_years < 10.0
assert before.major_lord == "SUN"
assert boundary.age_years == 10.0
assert boundary.major_lord == "VENUS"
assert boundary.minor_lord == "VENUS"
PY
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
assert major["strength"] == 0.65
assert minor["strength"] == 0.40
assert major["debug"]["age_years"] == 45.68767123
print(major["evidence"])
print(minor["evidence"])
PY
```

```bash
rg -n 'firdar_major|firdar_minor|major_period_lord|minor_period_lord|Sun is major firdar lord|Saturn is minor firdar lord' artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json
rg -n 'solar_return|lunar_return|secondary_progression|solar_arc|eclipse_window' artifacts/audit/2026-07-08/19_sidecar_activation_layer_w3_3_firdar.json || true
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff --name-only b00077a..HEAD
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-3-firdar/04_rework_01_report.md
```

Include:

- changed files;
- exact age/birthday fix;
- leap-day rule and test results;
- strict strength lookup proof;
- single-calculation proof;
- GRACE contract updates;
- node-period proof;
- fixture compatibility proof;
- artifact/hashseed proof;
- exact test results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.3 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-3-firdar/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
