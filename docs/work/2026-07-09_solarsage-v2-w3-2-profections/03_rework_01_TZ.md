# Rework 01 TZ: Fix W3.2 Monthly Boundaries and Audit Metadata

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Fix W3.2 blockers from `02_arch_review.md`.

Keep scope narrow:

- do not implement firdar, returns, progressions, eclipses;
- do not enable scoring v2;
- do not wire TodayService to sidecar activation layer;
- do not push/deploy.

## Required Fixes

### 1. Fix monthly profection month-step drift

Current code chains clamped dates and causes drift:

```python
probe = annual_year_start
next_probe = _add_months_with_clamp(probe, 1)
probe = next_probe
```

Replace with non-drifting anniversary counting from the original annual year start:

```python
completed_month_steps = 0
for step in range(1, 13):
    anniversary = _add_months_with_clamp(annual_year_start, step)
    if anniversary <= target_local:
        completed_month_steps = step
    else:
        break
```

Equivalent helper is fine, but it must calculate each anniversary from `annual_year_start`, not from the previous clamped anniversary.

Add tests using Basil annual year start `2025-10-30`:

```text
target 2026-03-29 => completed_month_steps 4
target 2026-03-30 => completed_month_steps 5
target 2026-07-29 => completed_month_steps 8
target 2026-07-30 => completed_month_steps 9
```

Also assert monthly house changes correctly:

```text
annual_house 10 + step 8 => monthly_house 6
annual_house 10 + step 9 => monthly_house 7
```

### 2. Add required debug fields

Add `house_cusp_longitude` to debug for all four required W3.2 activations:

- `annual_profection__HOUSE__10`
- `annual_profection__LORD_OF_YEAR__MARS`
- `monthly_profection__HOUSE__6`
- `monthly_profection__LORD_OF_MONTH__JUPITER`

For Basil `2026-07-08`, tests must assert:

```text
annual house_cusp_longitude = 0.0
annual house_cusp_sign = Aries
monthly house_cusp_longitude = 240.0
monthly house_cusp_sign = Sagittarius
```

### 3. Fix W3.2 audit metadata

Update `scripts/audit_sidecar_activation.py` so the artifact metadata is accurate.

Required:

- `_audit_meta.wave` is `W3.2` for the W3.2 command from `00_TZ.md`;
- `_audit_meta.techniques` contains the requested technique list when `--techniques` is provided;
- regenerate:

```text
artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
```

### 4. Do not silently map unknown signs to Saturn

Change:

```python
SIGN_RULERS.get(sign, "SATURN")
```

to a clear failure for unknown signs. Add a regression test:

```python
with pytest.raises(ValueError):
    _ruler_of_sign("NotASign")
```

### 5. Add timezone/local-date boundary test

Add one focused test proving the target `date` is treated as the local target date for profection boundaries.

Example acceptable test:

- target `2026-10-29`, time `23:30`, tz `Pacific/Kiritimati` => still local date `2026-10-29`, age `45`, house `10`;
- target `2026-10-30`, time `00:30`, tz `Pacific/Kiritimati` => local date `2026-10-30`, age `46`, house `11`.

The point is not UTC conversion. The point is that the request's local target date is the boundary input.

## Required Verification

Run and report exact results:

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_profections.py tests/test_activation_layer_endpoint.py tests/test_activation_transits.py tests/test_activation_schema.py -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_profections.py tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
python3 scripts/audit_sidecar_activation.py \
  --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
  --date 2026-07-08 \
  --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection \
  --out artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
git diff --exit-code -- artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
```

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py \
    --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
    --date 2026-07-08 \
    --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection \
    --out /tmp/sidecar_activation_w3_2_$i.json
  sha256sum /tmp/sidecar_activation_w3_2_$i.json
done
cmp -s /tmp/sidecar_activation_w3_2_1.json /tmp/sidecar_activation_w3_2_2.json
cmp -s /tmp/sidecar_activation_w3_2_1.json /tmp/sidecar_activation_w3_2_3.json
```

```bash
python3 - <<'PY'
import json
from pathlib import Path
p = Path("artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json")
data = json.loads(p.read_text())
print(data["_audit_meta"])
for aid in [
    "annual_profection__HOUSE__10",
    "annual_profection__LORD_OF_YEAR__MARS",
    "monthly_profection__HOUSE__6",
    "monthly_profection__LORD_OF_MONTH__JUPITER",
]:
    act = next(a for a in data["activations"] if a["id"] == aid)
    print(aid, act["debug"])
PY
```

```bash
rg -n 'annual_profection|monthly_profection|lord_of_year|lord_of_month|Annual profection activates house 10|Mars is lord of year|Monthly profection activates house 6|Jupiter is lord of month' artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json
rg -n 'firdar_major|firdar_minor|solar_return|lunar_return|secondary_progression|solar_arc|eclipse_window' artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json || true
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-2-profections/04_rework_01_report.md
```

Include:

- changed files;
- exact monthly boundary fix;
- Basil golden values after the fix;
- audit metadata proof;
- exact verification results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.2 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-2-profections/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-2-profections/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-2-profections/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
