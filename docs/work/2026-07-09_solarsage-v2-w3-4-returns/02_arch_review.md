# Architect Review — W3.4 Returns

Status: REWORK REQUIRED

Reviewed:

- `05cca74 docs(w3.4): finalize report with sha b754259`
- implementation commit: `b754259 W3.4: solar return + lunar return activations`
- report: `docs/work/2026-07-09_solarsage-v2-w3-4-returns/01_agent_report.md`

## Finding 1 — P0: `current_location` is accepted but not used for return houses

The request/debug contract says return houses must be built at `current_location` when supplied. Current implementation computes `ret_lat`/`ret_lon` in `activation_builder.py`, but then calls:

- `calculate_solar_return(... birth_lat=birth_lat, birth_lon=birth_lon, ...)`
- `calculate_lunar_return(... birth_lat=birth_lat, birth_lon=birth_lon, ...)`

See:

- `apps/solarsage/solarsage/services/activation_builder.py:1021`
- `apps/solarsage/solarsage/services/activation_builder.py:1046`
- `apps/solarsage/solarsage/services/activation_builder.py:1211`
- `apps/solarsage/solarsage/services/returns.py:238`
- `apps/solarsage/solarsage/services/returns.py:353`

Repro evidence from endpoint:

```text
birth_fallback ids == current_moscow ids == current_equator ids
current_equator first debug:
return_location_source=current_location
return_lat=0.0
return_lon=0.0
resolved_house_system=WHOLE_SIGN
```

For equator current location, `resolved_house_system` should not remain the birth-location high-latitude fallback. The debug payload currently says the return was relocated while the actual chart still uses birth coordinates.

## Finding 2 — P0: lunar return chooses smallest residual, not latest valid crossing

The TZ requires the most recent lunar return at or before target JD. Current code tracks `best_lon_residual` and chooses the crossing with the smallest residual:

- `apps/solarsage/solarsage/services/returns.py:313`
- `apps/solarsage/solarsage/services/returns.py:335`

This is wrong because multiple exact crossings all have tiny residuals. Selection must be by latest `return_jd <= target_jd`; residual is only a precision validation.

Repro evidence:

```text
target 2026-07-16 12:00 Europe/Moscow
current function return_jd: 2461209.5210913573
independent latest valid return_jd: 2461236.9515122585
diff: -27.430420901160687 days
```

That means for targets after the next lunar return, the layer can use the previous cycle.

## Finding 3 — P1: requested `house_system` is still ignored

The TZ says: use the requested house system where supported, preserve existing high-latitude resolution behavior, and expose the resolved house system. Current utility signature is:

```python
calculate_houses_cusps(jd: float, lat: float, lon: float)
```

and it always uses Placidus unless high latitude forces Whole Sign:

- `apps/solarsage/solarsage/utils/ephemeris.py:117`
- `apps/solarsage/solarsage/utils/ephemeris.py:126`

The W3.4 service passes `house_system`, but it is never forwarded into house calculation. This silently ignores the request.

## Finding 4 — P1: tests do not cover the real contract failures

The current tests would stay green while findings 1 and 2 are present.

Examples:

- `test_solar_return_location_source` checks only `debug.return_location_source`, not actual relocated ASC/MC/houses.
- lunar tests assert `return_jd <= target_jd` and `< 30 days`, but do not assert latest crossing.
- no focused tests prove missing `return_base` keys raise `KeyError`.
- index tests only loop over indexes and break on the first valid ref; they do not assert all return IDs are indexed correctly.
- API boundary debug fixture does not include all required return debug fields.
- report does not include the required combined W3.4 build elapsed time.

## Review Decision

Do not accept W3.4 yet. Fix the calculation contract first, then regenerate the audit artifact and rerun the full required verification list from `00_TZ.md`.
