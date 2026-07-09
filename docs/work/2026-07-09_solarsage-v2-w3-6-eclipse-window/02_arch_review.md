# W3.6 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `97d9c3e` implementation, `f9ad831` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/01_agent_report.md`

## Findings

### P1 — `eclipse_window` emits activations for non-nearest eclipses

File: `apps/solarsage/solarsage/services/eclipses.py:276-438`

The W3.6 TZ and source spec require selecting the nearest eclipse inside the configured date window, then activating natal planets/angles/lots only for that chosen eclipse point.

Current implementation sorts candidates by nearest first in `_find_eclipse_candidates()`, but `find_eclipses()` then iterates over every candidate returned:

```python
candidates = _find_eclipse_candidates(target_jd, config)
...
for cand in candidates:
```

This makes the implementation broader than the contract. A date can produce activations from a farther eclipse even when the nearest eclipse has no natal/angle/lot hit.

Reproduction:

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
acts = [a for a in r.json()["activation_layer"]["activations"] if a["technique"] == "eclipse_window"]
print(len(acts))
for a in acts:
    print(a["id"], a["debug"]["eclipse_kind"], a["debug"]["eclipse_date"], a["debug"]["days_delta"])
PY
```

Observed current output:

```text
2
eclipse_window__SOLAR__ANNULAR__2026_02_17__CONJUNCTION__NATAL_LOT_EROS solar 2026_02_17 -13.8667
eclipse_window__SOLAR__ANNULAR__2026_02_17__CONJUNCTION__NATAL_LOT_VICTORY solar 2026_02_17 -13.8667
```

But the nearest candidate for that target is the lunar eclipse on `2026_03_03` with `days_delta=0.1067`. Since that nearest lunar eclipse has no Basil natal/angle/lot target inside orb, expected result is zero `eclipse_window` activations.

Required behavior:
- collect previous/next solar/lunar candidates;
- filter by date window;
- select exactly one nearest candidate by `(abs_delta, eclipse_jd, eclipse_kind)`;
- build activations only from that chosen candidate;
- if the chosen candidate has no natal/angle/lot hits inside `orb_to_natal`, emit no eclipse activations.

### P2 — default-all endpoint test no longer protects W3.5 default support

File: `apps/solarsage/tests/test_activation_layer_endpoint.py:76-92`

The W3.6 update changed `test_activation_layer_endpoint_techniques_default_all()` to use an eclipse-positive date and removed checks for `solar_arc` and `secondary_progression`.

This makes the test no longer verify that the default empty `techniques` request includes W3.5 techniques. It is fine that not every supported technique necessarily produces activations on every date, but the default-order/support contract must still be covered without relying only on incidental activation presence.

Required behavior:
- keep W3.6 support coverage for `eclipse_window`;
- preserve W3.5 default support coverage for `solar_arc` and `secondary_progression`;
- avoid making default support assertions depend only on whether a technique happens to emit at least one activation for a fixture date.

Acceptable approaches:
- assert `ALL_TECHNIQUES` / `SUPPORTED_ORDER` contains the full deterministic W3.1-W3.6 order; and
- keep activation-producing endpoint tests as separate smoke tests for representative dates.

## Accepted Parts

These parts look architecturally aligned pending rework verification:
- sidecar-owned eclipse calculation, not API/frontend;
- no `TodayService` wiring;
- no scoring/convergence/frontend scope creep;
- canonical config keys present in `grace/canon/activation_rules.v1.yml`;
- API boundary validation for `eclipse_window` shape and index integrity;
- positive W3.6 audit artifact for Basil `2026-08-12`.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w3-6-eclipse-window/03_rework_01_TZ.md`.
