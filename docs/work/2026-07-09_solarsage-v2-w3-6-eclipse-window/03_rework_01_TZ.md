# W3.6 Rework 01 TZ — Nearest Eclipse Contract

Owner: coder in `tmux astro:0.0`
Architect/review: current Codex thread
Branch: `main`
Base: current `main` after W3.6 implementation/report
Push/deploy: do not push or deploy.

## Goal

Fix W3.6 `eclipse_window` so it implements the exact architectural contract:

```text
Find the nearest eclipse inside the configured date window, then emit activations only for natal/angle/lot conjunctions to that one chosen eclipse point.
```

Do not implement:
- scoring v2;
- convergence;
- TodayService wiring;
- semantic/LLM/frontend;
- push/deploy.

## Required Code Changes

### 1. Select exactly one nearest eclipse candidate

File:

```text
apps/solarsage/solarsage/services/eclipses.py
```

Current code sorts all candidates and iterates over all of them. Change the runtime behavior so `find_eclipses()` builds activations from exactly one chosen candidate:

```text
chosen = nearest candidate after date-window filtering
```

Tie-break must stay deterministic and match the W3.6 TZ:

```text
(abs_delta, eclipse_jd, eclipse_kind)
```

Where `eclipse_kind` is the canonical string `lunar` or `solar`. Do not use hidden or order-dependent tie-breaks.

Implementation shape is up to you, but one of these is acceptable:
- keep `_find_eclipse_candidates()` returning a sorted list, then in `find_eclipses()` use only `candidates[:1]`; or
- introduce `_find_nearest_eclipse_candidate()` and keep `_find_eclipse_candidates()` as test/debug helper.

If there is no candidate inside date window, return zero activations.

If the chosen candidate has no natal planet, angle, or lot within `orb_to_natal`, return zero activations.

Do not activate a farther eclipse just because it has natal hits.

### 2. Add a regression test for the current false positive

File:

```text
apps/solarsage/tests/test_eclipse_window.py
```

Add a test using Basil fixture:

```text
birth: 1980-10-30 19:50 Europe/Moscow, lat 67.9394, lon 32.8144
target: 2026-03-03 12:00 Europe/Moscow
house_system: PLACIDUS
techniques: ["eclipse_window"]
```

Expected:
- nearest candidate is the lunar eclipse on `2026_03_03`;
- no `eclipse_window` activations are emitted because that nearest lunar eclipse does not hit Basil natal/angle/lot targets within configured orb.

The test must fail against commit `97d9c3e` and pass after the fix.

### 3. Strengthen default support tests without relying on incidental activations

File:

```text
apps/solarsage/tests/test_activation_layer_endpoint.py
```

Preserve coverage that default empty `techniques` includes all supported W3.1-W3.6 techniques in deterministic order:

```text
transit_to_natal
transit_to_angle
transit_planet_in_house
transit_to_lot
annual_profection
monthly_profection
firdar_major
firdar_minor
solar_return
lunar_return
solar_arc
secondary_progression
eclipse_window
```

Do not assert this only by `techniques_found` from a single fixture's emitted activations, because some valid techniques can produce no activations on a particular date.

Preferred:
- import/check `ALL_TECHNIQUES` or `SUPPORTED_ORDER` for the deterministic default order; and
- keep separate endpoint smoke assertions for emitted representative activations where useful.

Make sure W3.5 techniques (`solar_arc`, `secondary_progression`) are not accidentally dropped from default support.

## Artifact

Regenerate the positive W3.6 audit artifact:

```text
artifacts/audit/2026-08-12/22_sidecar_activation_layer_w3_6_eclipse.json
```

The artifact should still contain at least one `eclipse_window` activation for Basil `2026-08-12`.

The artifact output must be deterministic across repeated hash seeds.

## Required Verification

Run and report exact results:

```bash
cd apps/solarsage && venv/bin/python -m pytest \
  tests/test_eclipse_window.py \
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
  tests/test_activation_layer_eclipse.py \
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
  --date 2026-08-12 \
  --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor,solar_return,lunar_return,solar_arc,secondary_progression,eclipse_window \
  --out artifacts/audit/2026-08-12/22_sidecar_activation_layer_w3_6_eclipse.json
```

```bash
set -e
for i in 1 2 3; do
  PYTHONHASHSEED=random python3 scripts/audit_sidecar_activation.py \
    --user-id eb3876be-e1b4-43d6-b887-1f8554e33150 \
    --date 2026-08-12 \
    --techniques transit_to_natal,transit_to_angle,transit_planet_in_house,transit_to_lot,annual_profection,monthly_profection,firdar_major,firdar_minor,solar_return,lunar_return,solar_arc,secondary_progression,eclipse_window \
    --out /tmp/sidecar_activation_w3_6_rework_01_$i.json
  sha256sum /tmp/sidecar_activation_w3_6_rework_01_$i.json
done
cmp -s /tmp/sidecar_activation_w3_6_rework_01_1.json /tmp/sidecar_activation_w3_6_rework_01_2.json
cmp -s /tmp/sidecar_activation_w3_6_rework_01_1.json /tmp/sidecar_activation_w3_6_rework_01_3.json
```

```bash
PYTHONPATH=/opt/solarsage-astro/apps/solarsage apps/solarsage/venv/bin/python - <<'PY'
from fastapi.testclient import TestClient
from solarsage.app import app

client = TestClient(app)
req = {
    "birth": {"date": "1980-10-30", "time": "19:50", "lat": 67.9394, "lon": 32.8144, "tz": "Europe/Moscow"},
    "target": {"date": "2026-03-03", "time": "12:00", "tz": "Europe/Moscow"},
    "house_system": "PLACIDUS",
    "techniques": ["eclipse_window"],
}
r = client.post("/v1/activation-layer", json=req)
assert r.status_code == 200, r.text
acts = [a for a in r.json()["activation_layer"]["activations"] if a["technique"] == "eclipse_window"]
assert acts == [], acts
print("nearest-no-hit eclipse regression passed")
PY
```

```bash
rg -n 'sidecar_activation_layer=None' apps/api/app/services/today_service.py
git diff 2f9173fbe9a9e20e97891e9789db6de57a2afaef..HEAD --check
git show --check HEAD
git status --short --branch
```

## Required Report

Write:

```text
docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/04_rework_01_report.md
```

Include:
- changed files;
- how nearest-candidate selection is now enforced;
- explicit result for Basil `2026-03-03` regression;
- default support/order test coverage for W3.1-W3.6;
- W3.6 artifact eclipse activation count;
- exact verification command results;
- hashseed SHA values;
- `sidecar_activation_layer=None` proof;
- commit SHA;
- push status `NOT_ATTEMPTED`.

Commit implementation, artifact, and report. Do not push or deploy.

## Callback

After implementation, verification, report, and commit, call:

```bash
curl -X POST http://127.0.0.1:18765/trigger \
  -H "Authorization: Bearer 324b0306c32ffc5f6a64e16076c8c9ac0ee12fbba925cfd3" \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Wave W3.6 Rework 01 ready for architect review. Report: docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/04_rework_01_report.md. Review: docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/02_arch_review.md. Rework TZ: docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/03_rework_01_TZ.md. Branch: main. Commit: <commit_sha>. Push: NOT_ATTEMPTED"}'
```
