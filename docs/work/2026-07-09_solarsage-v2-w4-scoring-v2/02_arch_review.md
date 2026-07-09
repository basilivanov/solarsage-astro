# W4 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `1be2c76` implementation, `29e4cb7` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/01_agent_report.md`

## Findings

### P1 — V2 base score is not the current V1 sphere formula

File: `apps/api/app/services/scoring_v2_service.py:137-170`

The W4 TZ requires:

```text
Base score is the current signal-derived sphere score before activation bonus.
Acceptable: instantiate ScoringService and call its existing _calculate_sphere_scores(day_signals)
```

The implementation duplicates the V1 formula instead of calling the helper, and the duplicate is incomplete. It omits the benefic/malefic modifier from `ScoringService._calculate_sphere_scores()`:

```text
apps/api/app/services/scoring_service.py:279-291
```

Fresh proof:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from app.schemas.normalization import AstroSignal
from app.services.scoring_service import ScoringService
from app.services.scoring_v2_service import _compute_v1_base_scores

signals = [AstroSignal(
    type="aspect",
    planet="Transit_Mercury",
    target_planet="Venus",
    aspect_type="square",
    orb=1.0,
    strength=1.0,
    kind="aspect",
)]
print(ScoringService()._calculate_sphere_scores(signals)["thinking_speech_learning"])
print(_compute_v1_base_scores(signals)["thinking_speech_learning"])
PY
```

Observed:

```text
1.05
0.85
```

This breaks the W4 contract and will make W5 dual-run compare a different baseline than V1.

### P1 — inactive activations contribute to scoring and status

File: `apps/api/app/services/scoring_v2_service.py:431-459`
File: `apps/api/app/services/scoring_v2_service.py:326-332`

The W4 TZ says activation contribution is for active activations. Current code loops over all `activation_layer.activations` in both sphere contribution and day status calculations without checking `active`.

Fresh proof:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service

layer = ActivationLayer(
    calculation_version="1",
    target_date="2026-07-08",
    target_time="12:00",
    target_tz="Europe/Moscow",
    house_system="WHOLE_SIGN",
    activations=[ActivationEvidence(
        id="inactive_mercury",
        technique="annual_profection",
        technique_family="profection",
        target_type="planet",
        target_key="MERCURY",
        kind="lord",
        active=False,
        phase="period",
        strength=1.0,
        polarity="supportive",
        evidence="inactive should not count",
    )],
    by_planet={"MERCURY": ["inactive_mercury"]},
    by_house={},
    by_lot={},
    by_angle={},
)
r = ScoringV2Service().score_day([], layer)
print(r.sphere_scores["thinking_speech_learning"].activation_score)
print(r.status_breakdown["activation_support_score"])
PY
```

Observed:

```text
0.8
0.8
```

Expected: both values are `0.0`.

### P1 — day status V2 does not apply V1 aspect thresholds

File: `apps/api/app/services/scoring_v2_service.py:310-320`

The W4 TZ requires status aspect scores to use the same aspect weights and thresholds as V1. `ScoringService._calculate_day_status()` applies `_aspect_threshold(_is_major(...))` before accumulating status scores. V2 does not.

Fresh proof:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api apps/api/.venv/bin/python - <<'PY'
from app.schemas.normalization import AstroSignal
from app.services.scoring_service import ScoringService
from app.services.scoring_v2_service import ScoringV2Service

signals = [
    AstroSignal(
        type="aspect",
        planet=f"Transit_Moon_{i}",
        target_planet="Mars",
        aspect_type="trine",
        orb=4.0,
        strength=0.2,
        kind="aspect",
    )
    for i in range(7)
]
print(ScoringService().score_day(signals)["day_status"])
r = ScoringV2Service().score_day(signals, None)
print(r.day_status, r.status_breakdown["positive_aspect_score"])
PY
```

Observed:

```text
steady
supportive 1.19
```

Each weak aspect should be below V1 threshold and contribute zero to the V2 status breakdown.

### P1 — convergence test changes the required bound instead of testing it

File: `apps/api/tests/test_scoring_v2_convergence.py:24-84`

The W4 TZ requires the Mercury/profection/Saturn test to prove:

```text
thinking_speech_learning.post_bonus >= 1.4 * base_score
thinking_speech_learning.post_bonus <= 2.0 * base_score
```

The test docstring still says this, but the actual assertion was changed to:

```python
assert post_bonus >= 2.0 * ss.base_score
assert ss.dominance_capped
```

There is no upper-bound assertion. This is not an acceptable substitute for the required convergence scenario. Anti-dominance cap coverage belongs in the separate anti-dominance test.

### P1 — Basil golden test deletes tracked audit artifacts

File: `apps/api/tests/test_basil_2026_07_08_v2_golden.py:68-70`

The test writes to required tracked artifact paths and then deletes them:

```python
result_path.unlink(missing_ok=True)
diff_path.unlink(missing_ok=True)
```

Running the test leaves required W4 artifacts missing from the working tree. Tests must not delete tracked deliverables. Use `tmp_path` for test output, or regenerate tracked artifacts outside pytest as a required command.

### P2 — audit artifact key style fails the W4 verification command

File: `scripts/audit_scoring_v2.py:80-85`
Artifact: `artifacts/audit/2026-07-08/22_scoring_v2_result.json`

The script writes `ScoringV2Result` with `by_alias=True`, producing camelCase keys:

```json
{
  "scoringVersion": "ss-scoring-2.0"
}
```

The W4 TZ verification command checks snake_case:

```python
assert result["scoring_version"] == "ss-scoring-2.0"
```

Fresh proof:

```text
has scoring_version False
has scoringVersion True
KeyError 'scoring_version'
```

For W4 audit artifacts, use snake_case serialization so the documented gate is authoritative and deterministic. API JSON aliasing can remain a later boundary concern.

### P2 — runtime constants are hidden fallbacks instead of canon-owned values

File: `apps/api/app/services/scoring_v2_service.py`

The W4 TZ says not to hardcode W4 scoring values in Python. The current implementation uses several hidden fallback constants:

```text
family independence weight: 1.0
target defaults: house 0.8, lot 0.8, angle 0.7, sphere 1.0
convergence default: 0.0 / 1.0
dominance threshold: 0.65
status thresholds: 1.3 / 1.0
activation polarity modifiers: 0.0 / 1.0
```

For required canon keys, missing config should fail loudly through strict helpers, not silently change semantics.

### P2 — service contract comment contradicts actual W4 semantics

File: `apps/api/app/services/scoring_v2_service.py:18-23`

The module invariant says:

```text
Activation contributions use strongest matching activation per sphere
```

W4 requires every active activation-sphere match to contribute. The current code mostly follows W4, but the invariant is wrong and can lead to future regression.

### P2 — new audit script does not follow the requested GRACE module style

File: `scripts/audit_scoring_v2.py:1-13`

The W4 TZ requires new Python modules to follow the local GRACE comment style:

```text
module header;
module contract;
module map;
function contracts for non-trivial functions;
no grace_control import.
```

`scripts/audit_scoring_v2.py` starts with a shebang and docstring only.

## Accepted Parts

These parts are architecturally aligned pending rework verification:

- W4 is isolated from `TodayService`, `CalendarService`, frontend, generated contracts, cache keys, flags, LLM, and sidecar.
- `ScoringV2Service.score_day()` returns the existing `ScoringV2Result` schema.
- Activation target mapping covers planet, house, lot, angle, and sphere.
- Tense activations are not dropped from sphere salience.
- Convergence is represented as explicit contributions and debug family data.
- Anti-dominance cap is represented as an explicit negative contribution.
- Audit script is pure local IO and does not call external services.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/03_rework_01_TZ.md`.
