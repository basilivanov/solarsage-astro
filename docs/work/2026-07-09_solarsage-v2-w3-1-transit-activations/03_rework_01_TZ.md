# Rework 01 TZ: Stabilize W3.1 Transit Activations

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: main
Push/deploy: do not push/deploy before architect review

## Goal

Fix W3.1 blockers from `02_arch_review.md` without expanding beyond transit-family activation extraction.

Do not enable scoring v2. Do not wire TodayService to the sidecar layer.

## Required Fixes

### 1. Make the audit script runnable from repo root

Current command fails:

```bash
python3 scripts/audit_sidecar_activation.py ...
```

because system `python3` does not have `swisseph`.

Fix one of these ways:

Preferred:

- In `scripts/audit_sidecar_activation.py`, detect when the current interpreter is not `apps/solarsage/venv/bin/python` and re-exec into that venv python if it exists.
- Keep the documented command runnable:

```bash
python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

Acceptable alternative:

- Update the script/report/TZ references to use this command and prove it works:

```bash
PYTHONPATH=apps/solarsage apps/solarsage/venv/bin/python scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

### 2. Make default technique ordering deterministic

Replace:

```python
W3_1_SUPPORTED = {...}
ALL_TECHNIQUES = list(W3_1_SUPPORTED)
```

with explicit ordering:

```python
W3_1_SUPPORTED_ORDER = (
    "transit_to_natal",
    "transit_to_angle",
    "transit_planet_in_house",
    "transit_to_lot",
)
W3_1_SUPPORTED = set(W3_1_SUPPORTED_ORDER)
ALL_TECHNIQUES = list(W3_1_SUPPORTED_ORDER)
```

Rules:

- empty `techniques` uses `ALL_TECHNIQUES`;
- explicit `techniques` preserves caller order after filtering unsupported techniques;
- unsupported warnings are deterministic and in request order.

Add test:

- build the same default activation layer twice;
- assert `[a.id for a in layer.activations]` is identical.

Also run a hash-seed check in verification:

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out /tmp/sidecar_activation_$i.json
  sha256sum /tmp/sidecar_activation_$i.json
done
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_2.json
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_3.json
```

### 3. Fix applying/separating calculation

Replace raw angular-distance comparison with orb comparison:

```python
current_orb = abs(adist - ASPECT_ANGLES[best_aspect])
probe_orb = abs(probe_adist - ASPECT_ANGLES[best_aspect])

if abs(probe_orb - current_orb) < tolerance:
    applying = False
    phase = "exact"
elif probe_orb < current_orb:
    applying = True
    phase = "applying"
else:
    applying = False
    phase = "separating"
```

Add regression for Basil Moon-Pluto:

- activation id `t2n__MOON__OPPOSITION__PLUTO`;
- evidence includes `Transit Moon opposition natal Pluto`;
- orb is within `0.05` of `1.0454`;
- `phase == "separating"`;
- `applying is False`.

### 4. Make evidence human-readable while keeping keys canonical

Change evidence display text for planets from all-caps target keys to title/display names.

Required:

- `target_key` remains uppercase, e.g. `PLUTO`;
- `by_planet["PLUTO"]` remains uppercase;
- evidence uses `Pluto`, e.g. `Transit Moon opposition natal Pluto, orb 1.0454°`;
- angle evidence remains `natal MC`, `natal ASC`, etc.;
- lot evidence may keep lot names uppercase, e.g. `lot FORTUNE`.

### 5. Strengthen tests

In sidecar tests:

- Rename the non-Basil fixture from `BASIL_REQUEST` to something accurate like `MOSCOW_FIXTURE_REQUEST`.
- Add `BASIL_AUDIT_REQUEST` with real Basil audit data:

```python
{
    "birth": {
        "date": "1980-10-30",
        "time": "19:50",
        "lat": 67.9394,
        "lon": 32.8144,
        "tz": "Europe/Moscow",
    },
    "target": {
        "date": "2026-07-08",
        "time": "12:00",
        "tz": "Europe/Moscow",
    },
    "house_system": "PLACIDUS",
    "techniques": [],
}
```

Replace tautological assertions:

```python
assert len(total_lot_refs) >= 0
```

with real assertions:

- `by_lot` is non-empty for Basil audit request;
- all `by_lot` refs point to valid activation ids;
- the set of lot names in activation debug/index includes:
  - `FORTUNE`
  - `SPIRIT`
  - `EROS`
  - `MARRIAGE`
  - `NECESSITY`
  - `VICTORY`
  - `NEMESIS`

Add or update tests so they fail on:

- non-deterministic default technique order;
- wrong applying/separating for Moon-Pluto;
- uppercase `natal PLUTO` evidence.

### 6. Regenerate audit artifact

Regenerate:

```text
artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

Then rerun the script and prove:

```bash
git diff --exit-code -- artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

Expected artifact now contains:

- `Transit Moon opposition natal Pluto`;
- Moon-Pluto `phase="separating"`;
- Moon-Pluto `applying=false`;
- stable activation ordering across processes.

### 7. Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/04_rework_01_report.md
```

Include:

- changed files;
- exact fixes for script runner, deterministic order, phase/applying, evidence display;
- Basil Moon-Pluto evidence/orb/phase/applying;
- deterministic hash-seed verification results;
- exact test results;
- commit SHA;
- push status `NOT_ATTEMPTED`.

## Required Verification

Run and report exact results:

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/test_activation_transits.py tests/test_activation_layer_endpoint.py tests/test_activation_schema.py -q
```

```bash
cd apps/solarsage && venv/bin/python -m pytest tests/ -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/test_activation_layer_transits.py tests/test_activation_layer_contract.py tests/test_today_meta_versions.py tests/test_astronomy_oracle.py -q
```

```bash
cd apps/api && source .venv/bin/activate && python -m pytest tests/ -q
```

```bash
python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
git diff --exit-code -- artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
```

```bash
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 --date 2026-07-08 --out /tmp/sidecar_activation_$i.json
  sha256sum /tmp/sidecar_activation_$i.json
done
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_2.json
cmp -s /tmp/sidecar_activation_1.json /tmp/sidecar_activation_3.json
```

```bash
rg -n 'Transit Moon opposition natal Pluto|\"phase\": \"separating\"|\"applying\": false|transit_to_angle|transit_to_lot|transit_planet_in_house' artifacts/audit/2026-07-08/17_sidecar_activation_layer.json
rg -n 'annual_profection|firdar_major|solar_return|secondary_progression|eclipse_window|natal PLUTO' artifacts/audit/2026-07-08/17_sidecar_activation_layer.json || true
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

Do not run `pnpm build` or restart production frontend for this rework.

## Callback

After committing and writing the report, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.1 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-1-transit-activations/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
