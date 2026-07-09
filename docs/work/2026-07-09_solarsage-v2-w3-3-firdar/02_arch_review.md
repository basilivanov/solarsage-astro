# W3.3 Architect Review — Firdar Activations

Status: REWORK REQUIRED
Date: 2026-07-09
Branch: main
Reviewed commits:

- `15f9b1c` — W3.3 implementation
- `e20e4d6` — report SHA correction

## Findings

### P0 — Decimal age can cross a Firdar boundary one day early

File:

```text
apps/solarsage/solarsage/services/firdar.py
```

Current code divides elapsed days by the number of days in the calendar year containing the last birthday:

```python
days_in_birth_year = _days_in_year(birthday_this_year.year)
```

The W3.3 contract requires the actual interval between the previous and next birthday:

```text
days_in_current_birthday_year = next_birthday - last_birthday
```

These differ when a birthday interval crosses February 29.

Independent reproduction on current code:

```bash
cd apps/solarsage && venv/bin/python - <<'PY'
from datetime import date
from solarsage.services.firdar import calculate_firdar, _load_firdar_canon
ctx = calculate_firdar(
    birth_local=date(1990, 7, 1),
    target_local=date(2000, 6, 30),
    is_day_birth=True,
    sun_house=9,
    canon=_load_firdar_canon(),
)
print(ctx.age_years, ctx.major_lord, ctx.minor_lord)
PY
```

Actual:

```text
10.0 VENUS VENUS
```

Expected one day before the 10th birthday:

```text
age_years < 10.0
major_lord = SUN
```

This violates the exact-boundary semantics and changes the active period early.

### P1 — Firdar strengths silently fall back to product constants

File:

```text
apps/solarsage/solarsage/services/activation_builder.py
```

Current:

```python
major_strength = float(period_base.get("firdar_major", 0.65))
minor_strength = float(period_base.get("firdar_minor", 0.40))
```

The W3.3 contract explicitly requires canon values to be mandatory. Missing values must fail clearly, not silently preserve hidden defaults.

Use the existing strict `_get_period_strength()` path and add a regression test for missing Firdar strength keys.

### P1 — New Firdar module does not satisfy AGENTS.md GRACE contracts

File:

```text
apps/solarsage/solarsage/services/firdar.py
```

The file has `AI_HEADER`, but it is missing:

- `START_MODULE_CONTRACT`;
- `START_MODULE_MAP`;
- function contracts for public/non-trivial functions;
- named semantic blocks.

`00_TZ.md` explicitly required the new module to follow `AGENTS.md`.

Do not import `grace_control`; use comment contracts only, as required by repository AGENTS.md.

### P1 — Leap-day birth is not supported

File:

```text
apps/solarsage/solarsage/services/firdar.py
```

This construction raises on non-leap target years for a February 29 birth:

```python
Date(target_local.year, birth_local.month, birth_local.day)
```

The period service must define deterministic birthday clamping consistent with the W3.2 calendar-month philosophy. Add tests for a February 29 birth in both leap and non-leap target years.

### P2 — Firdar context is recalculated once per technique

File:

```text
apps/solarsage/solarsage/services/activation_builder.py
```

With default techniques, the loop enters once for `firdar_major` and once for `firdar_minor`, loading canon and recomputing natal-period context twice.

The W3.3 contract requires the context to be computed once when either technique is active. Cache/precompute the context and strengths once, then emit requested activations independently.

Add a focused test proving `calculate_firdar()` is called once when both techniques are requested.

### P2 — Node periods are implemented but not behaviorally tested

Files:

```text
apps/solarsage/solarsage/services/firdar.py
apps/solarsage/tests/test_firdar.py
```

The service has special node-period logic, but tests only validate canon list lengths/order. Add behavioral tests for:

- age `70.0` => `NORTH_NODE_TRUE` major, first node minor `SATURN`;
- age `73.0` => `SOUTH_NODE` major, first node minor `SATURN`;
- stable ids and `by_planet` refs for node lords;
- readable evidence names (`North Node`, `South Node`), not raw underscore keys.

### P2 — Historical fixture compatibility is asserted indirectly

File:

```text
apps/solarsage/tests/test_firdar.py
```

The tests hardcode expected lords but do not read:

```text
apps/solarsage/tests/fixtures/test_user_2026-06-15.json
apps/solarsage/tests/fixtures/vasiliy_2026-05-30.json
```

Load the fixture Firdaria payloads and compare the canon sequence/year/subperiod order against `raw.firdaria.value.periods`. This turns the historical compatibility claim into executable evidence.

## What Passed

The implementation is otherwise scoped correctly:

- only W3.3 techniques were added;
- sidecar owns the calculation;
- API remains a validator;
- `TodayService` remains unwired;
- W3.3 artifact metadata reports `wave=W3.3`;
- Basil artifact contains:
  - `firdar_major__PERIOD_LORD__SUN`;
  - `firdar_minor__SUBPERIOD_LORD__SATURN`;
- future return/progression/eclipse techniques are absent from the W3.3 artifact;
- no push/deploy was attempted.

## Decision

Do not accept W3.3 yet.

Complete `03_rework_01_TZ.md`, regenerate the W3.3 artifact, rerun all required gates, commit, and call the architect callback.
