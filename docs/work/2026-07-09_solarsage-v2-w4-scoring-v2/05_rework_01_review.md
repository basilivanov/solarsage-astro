# W4 Rework 01 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `6c777da` implementation, `4e98d97` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/04_rework_01_report.md`

## Fresh Verification Performed

Targeted V2 tests:

```bash
cd apps/api && source .venv/bin/activate && python -m pytest \
  tests/test_scoring_v2_contracts.py \
  tests/test_scoring_v2_convergence.py \
  tests/test_scoring_v2_antidominance.py \
  tests/test_scoring_v2_thresholds.py \
  tests/test_scoring_v2_family_dedup.py \
  tests/test_scoring_v2_breakdown_contract.py \
  tests/test_basil_2026_07_08_v2_golden.py -q
```

Observed:

```text
18 passed in 0.39s
```

W4 artifact shape validation:

```text
scoring_version ss-scoring-2.0
camel_scoringVersion_present False
sphere_scores 9
has_activation True
has_convergence True
diffs 9
```

## Findings

### P1 — Required W4 diff artifact is dirty after callback

File: `artifacts/audit/2026-07-08/23_scoring_v2_diff.json`

After the coder reported callback success, the working tree still had a tracked modification:

```bash
git status --short --branch
```

Observed:

```text
## main...origin/main [ahead 114]
 M artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

`6c777da` committed `22_scoring_v2_result.json` but did not commit `23_scoring_v2_diff.json`:

```text
6c777da W4 Rework 01: fix base scores, inactive activations, thresholds, constants
apps/api/app/services/scoring_v2_service.py
apps/api/tests/test_basil_2026_07_08_v2_golden.py
apps/api/tests/test_scoring_v2_breakdown_contract.py
apps/api/tests/test_scoring_v2_convergence.py
apps/api/tests/test_scoring_v2_thresholds.py
artifacts/audit/2026-07-08/22_scoring_v2_result.json
docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/04_rework_01_report.md
scripts/audit_scoring_v2.py
```

The original W4 TZ and Rework 01 TZ both require regenerating and committing both artifacts:

```text
artifacts/audit/2026-07-08/22_scoring_v2_result.json
artifacts/audit/2026-07-08/23_scoring_v2_diff.json
```

The report also claims "Working tree | Tracked artifacts present, not deleted", but the current state contradicts that claim. W4 cannot be accepted with a dirty tracked artifact.

### P2 — Required canon values still have hidden runtime fallbacks

File: `apps/api/app/services/scoring_v2_service.py`

Rework 01 required missing W4 canon keys to fail loudly. Several required values still use `.get(..., constant)`:

```text
apps/api/app/services/scoring_v2_service.py:230
apps/api/app/services/scoring_v2_service.py:247
apps/api/app/services/scoring_v2_service.py:326-327
apps/api/app/services/scoring_v2_service.py:436
apps/api/app/services/scoring_v2_service.py:543
```

Fresh proof for missing polarity modifiers:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from copy import deepcopy
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service
import app.services.scoring_v2_service as svc

orig = deepcopy(svc._get_scoring_v2())
mut = deepcopy(orig)
del mut["activation_polarity"]["sphere_amount_modifier"]["neutral"]
del mut["activation_polarity"]["status_support_modifier"]["neutral"]
del mut["activation_polarity"]["status_tension_modifier"]["neutral"]
svc._SCORING_V2 = mut
try:
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[ActivationEvidence(
            id="neutral_missing_key",
            technique="annual_profection",
            technique_family="profection",
            target_type="planet",
            target_key="MERCURY",
            kind="lord",
            phase="period",
            strength=1.0,
            polarity="neutral",
            evidence="neutral should require canon modifier",
        )],
        by_planet={"MERCURY": ["neutral_missing_key"]},
        by_house={},
        by_lot={},
        by_angle={},
    )
    r = ScoringV2Service().score_day([], layer)
    print("NO_KEYERROR", r.sphere_scores["thinking_speech_learning"].activation_score)
except KeyError as e:
    print("KEYERROR", e)
finally:
    svc._SCORING_V2 = orig
PY
```

Observed:

```text
NO_KEYERROR 0.8
```

Expected: `KeyError`.

Fresh proof for missing convergence curve entry:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from copy import deepcopy
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service
import app.services.scoring_v2_service as svc

orig = deepcopy(svc._get_scoring_v2())
mut = deepcopy(orig)
del mut["convergence_curve"][3]
svc._SCORING_V2 = mut
try:
    acts = [
        ActivationEvidence(id="p", technique="annual_profection", technique_family="profection", target_type="planet", target_key="MERCURY", kind="lord", phase="period", strength=0.1, polarity="supportive", evidence="p"),
        ActivationEvidence(id="t", technique="transit_to_natal", technique_family="transit", target_type="planet", target_key="MERCURY", kind="trine", phase="period", strength=0.1, polarity="supportive", evidence="t"),
        ActivationEvidence(id="f", technique="firdar_major", technique_family="firdar", target_type="planet", target_key="MERCURY", kind="lord", phase="period", strength=0.1, polarity="supportive", evidence="f"),
    ]
    layer = ActivationLayer(calculation_version="1", target_date="2026-07-08", target_time="12:00", target_tz="Europe/Moscow", house_system="WHOLE_SIGN", activations=acts, by_planet={"MERCURY": ["p", "t", "f"]}, by_house={}, by_lot={}, by_angle={})
    r = ScoringV2Service().score_day([], layer)
    print("NO_KEYERROR", r.sphere_scores["thinking_speech_learning"].convergence_bonus)
except KeyError as e:
    print("KEYERROR", e)
finally:
    svc._SCORING_V2 = orig
PY
```

Observed:

```text
NO_KEYERROR 0.0
```

Expected: `KeyError`.

### P2 — dead global state left in the pure service

File: `apps/api/app/services/scoring_v2_service.py:73`

The service defines:

```python
_ACTIVE_ACTIVATIONS: list[ActivationEvidence] | None = None
```

It is unused. W4 is a pure service; unused module-level mutable state should not be left around.

## Accepted Parts

These Rework 01 changes look aligned pending the remaining fixes:

- base score now reuses `ScoringService()._calculate_sphere_scores(day_signals)`;
- inactive activations are skipped in sphere contribution/status/top activations;
- V2 status applies V1 aspect thresholds;
- Mercury convergence test restored the `>= 1.4x` and `<= 2.0x` bounds;
- Basil golden test uses `tmp_path`;
- `22_scoring_v2_result.json` is now snake_case and validates as `ScoringV2Result`;
- audit script has GRACE-style header/contract/map.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/06_rework_02_TZ.md`.
