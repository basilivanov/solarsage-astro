# Wave W0 Architect Review

Status: REWORK REQUIRED

Reviewed commit: `b8ef9138d97cd7eafe5a29cafcad02fa48616cf8`
Base: `2f9173fbe9a9e20e97891e9789db6de57a2afaef`

## Findings

### P0 — Audit exits successfully while astronomy oracle fails

Fresh architect run:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

Exit code: `0`.

Actual `13_astronomy_oracle_summary.json`:

```json
{
  "moon_phase": {
    "oracle_percent": 43.792,
    "production_percent": 46,
    "delta_percent": -2.208,
    "pass": false
  }
}
```

The final payload is still served from a version-5 cache created before the Moon illumination fix:

```text
final_cached=true
Убывающая Луна 46%
```

Impact:

- W0 DoD says astronomy oracle must pass.
- The command currently reports success for a failed trust check.
- The agent report incorrectly claims production `43.792%`.

Required:

- bump `TODAY_CONTENT_VERSION` from `5` to `6`;
- update tests asserting the version;
- regenerate Basil `2026-07-08` payload through the production path;
- display Moon illumination with rounding that stays within the specified `<= 0.5pp` tolerance (`round`, not truncating `int`);
- make astronomy/scoring oracle failures propagate to non-zero `make audit-day`;
- add a regression test proving a failed oracle makes the command/script fail.

### P0 — Retrograde remains silently defaulted to false

Current code:

```python
apps/solarsage/solarsage/schemas/natal.py:
retrograde: bool = False

apps/api/app/schemas/natal.py:
SolarSagePlanetPosition.retrograde: bool = False
SolarSageTransitPlanet.retrograde: bool = False
```

Also, `apps/solarsage/solarsage/services/calculator.py::calculate_planets()` still emits `speed` but not `retrograde`, so the natal sidecar path continues to use the false default.

Impact:

- missing data is still indistinguishable from a direct planet;
- natal Mercury/Neptune/Pluto may still be silently wrong;
- the current test only calls the running transit sidecar happy path.

Required:

- sidecar `Planet.retrograde` must be required, not default `False`;
- both ephemeris/transit and natal calculator paths must emit `retrograde = speed < 0`;
- API sidecar schemas must use `retrograde: bool | None = None` and derive it from `speed` when omitted;
- if both `retrograde` and `speed` are absent, fail validation in test/dev/audited paths;
- add unit tests for transit and natal calculation plus API schema derivation/failure;
- add the requested `apps/solarsage/tests/test_ephemeris_retrograde.py`.

### P0 — Day/natal evidence separation is incomplete

`build_why_contexts()` accepts the new arguments, but still builds:

```python
src = all_signals if all_signals else top_signals
aspects = [...]
```

Only `planet_in_house` was partially filtered with `transit_houses`. Static natal aspects can still become:

- `top_aspect`;
- daily layer evidence;
- personal activation;
- amplifiers;
- softeners.

The new test covers only natal house contamination and invokes the fallback rather than the explicit separated contract.

Required:

- all current-day contexts must source aspects/houses from `day_scored_signals`;
- natal background may use `natal_background_signals` only in an explicitly labeled natal/background context;
- `all_signals` may remain compatibility input, but must not be the authoritative source for day evidence;
- test explicit arguments and prove both natal house and natal aspect signals cannot appear as current-day evidence;
- preserve useful natal sign/house details in the correctly labeled natal background instead of deleting them.

### P1 — Advice guard rejects the allowed mitigation from the specification

The W0 allowed example is:

```text
Если нужно общаться с близкими — выбирай короткий, спокойный формат и не разбирай острые темы.
```

Current substring guard rejects it because it finds `общаться` without one of the narrow 15-character negative prefixes.

Required:

- add the exact allowed example as a passing test;
- keep `Общайся с близкими для улучшения отношений` as a failing test;
- support conditional/mitigation language such as `если нужно`, `только`, `короткий формат`, `избегай`, `не`;
- add an explicit `avoid` rule to the `generate_concrete_advice` prompt so the LLM is guided before post-validation.

### P1 — Moon phase regression test does not test production behavior

`test_moon_phase_illumination_2026_07_08` fetches Sun/Moon positions and recomputes the oracle formula inside the test. It would pass even if `TodayInterpretationService` still used the old formula.

Required:

- extract/test a production illumination helper or build a real `DayChart` through `TodayInterpretationService`;
- assert the produced fact is based on `43.792%` and displays a correctly rounded value;
- retain independent oracle comparison separately.

### P1 — Audit artifact generator is case-hardcoded and root output is duplicated

`scripts/audit_today.py` writes `14_claims_audit.md` and `15_audit_summary.md` with hardcoded Basil/date/scores/claims. Running it for another user/date would create a false report.

The artifact directory also contains the 16 canonical files plus many duplicate legacy files. The agent report says 18 total, while the directory contains substantially more.

Required:

- generate report identity/date/status/scores from actual inputs and computed artifacts;
- case-specific claim rows may be explicitly labeled as a Basil golden snapshot, but generic runs must not claim Basil facts;
- make the root artifact contract unambiguous: canonical 16 files at root; optional detailed/debug artifacts may live under a documented `debug/` subdirectory;
- correct README and report counts.

### P2 — Commit hygiene

`git show --check b8ef913` fails on trailing whitespace in Python/tests and CRLF CSV output.

The report contains stale commit `56f6653`, while the reviewed commit is `b8ef913`.

Required:

- remove code/test trailing whitespace;
- configure CSV writer with `lineterminator="\n"`;
- make `git show --check HEAD` pass;
- update report with the final commit SHA after the final commit, or state a stable reviewed range without self-referential stale SHA.

## Fresh Verification Evidence

Passed:

```text
30 passed, 1 warning
```

from:

```bash
apps/api/.venv/bin/python -m pytest \
  apps/api/tests/test_astronomy_oracle.py \
  apps/api/tests/test_semantic_contexts.py \
  apps/api/tests/test_today_concrete_advice_consistency.py \
  apps/api/tests/test_today_concrete_advice.py \
  apps/api/tests/test_day_endpoints.py \
  apps/api/tests/test_calendar_endpoints.py -q
```

Passed:

```bash
apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py
```

Failed acceptance despite exit code 0:

```text
moon_phase.pass=false
production_percent=46
oracle_percent=43.792
```

from:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```
