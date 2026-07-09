# W3.3 Rework 01 Architect Review

Status: REWORK REQUIRED
Date: 2026-07-09
Branch: main
Reviewed commits:

- `568cbdf` — W3.3 Rework 01 implementation
- `30b11c6` — Rework 01 report SHA correction

## Fresh Verification

The functional fixes are real and pass:

```text
sidecar targeted: 63 passed, 1 warning
sidecar full: 84 passed, 1 warning
API targeted: 23 passed
API full: 690 passed, 5 skipped, 1 warning
```

Manual checks:

```text
birth 1990-07-01, target 2000-06-30:
age=9.997267759563, major=SUN

birth 1990-07-01, target 2000-07-01:
age=10.0, major=VENUS, minor=VENUS

age=70.0:
major=NORTH_NODE_TRUE, minor=SATURN

age=73.0:
major=SOUTH_NODE, minor=SATURN
```

W3.3 artifact:

```text
117 activations
wave=W3.3
major=SUN
minor=SATURN
hashseed deterministic
```

## Resolved Findings

- decimal age now uses the actual birthday interval;
- February 29 clamping is implemented;
- Firdar strength lookup is strict;
- `calculate_firdar()` is called once per request;
- node display names are readable;
- `TodayService` remains unwired;
- no push/deploy was attempted.

## Remaining Findings

### P1 — Historical fixture contract is still only partially tested

File:

```text
apps/solarsage/tests/test_firdar.py
```

`03_rework_01_TZ.md` required executable comparison of:

- all major lords;
- major years/start/end ages;
- every seven-planet subperiod lord order;
- node periods and node minor sequence;
- both day and night fixtures.

Current tests compare:

- only the first seven major lord keys;
- one first-period years value;
- one first-period subperiod order;
- current major lord.

They do not compare all nine periods, all period boundaries, or all subperiod rotations.

Also, the legacy fixture has an important semantic limitation:

```text
test_user_2026-06-15.json current_sub_period = MARS
```

The current date-precise implementation correctly returns:

```text
minor = SUN
```

The old collector called Firdaria with integer age `36`, so its `current_sub_period` is not a valid oracle for the date-precise W3.3 algorithm. The report currently says active lords are verified without documenting this distinction.

### P1 — GRACE function contracts are incomplete

File:

```text
apps/solarsage/solarsage/services/firdar.py
```

Module contract/map were added, but the non-trivial date helpers still lack `START_FUNCTION_CONTRACT` blocks:

- `_clamp_birthday`;
- `_completed_years`;
- `_last_birthday`;
- `_next_birthday`;
- `_age_years_decimal`.

The Rework 01 TZ explicitly required function contracts for non-trivial internal calculation functions.

The module contract also mentions unknown signs, which this module does not process. Update failure policy/invariants to describe actual Firdar failures.

### P2 — Activation rules are still loaded twice

File:

```text
apps/solarsage/solarsage/services/activation_builder.py
```

Current:

```python
major_strength = _get_period_strength(_load_activation_rules(), "firdar_major")
minor_strength = _get_period_strength(_load_activation_rules(), "firdar_minor")
```

Load once:

```python
activation_rules = _load_activation_rules()
major_strength = _get_period_strength(activation_rules, "firdar_major")
minor_strength = _get_period_strength(activation_rules, "firdar_minor")
```

### P2 — Node endpoint assertions do not prove stable ids/evidence

Current node endpoint tests only prove that raw underscore keys are absent and that some `by_planet` reference exists.

Add exact assertions for:

```text
firdar_major__PERIOD_LORD__NORTH_NODE_TRUE
firdar_major__PERIOD_LORD__SOUTH_NODE
```

and exact readable evidence prefixes:

```text
North Node is major firdar lord
South Node is major firdar lord
```

## Decision

Do not accept W3.3 yet.

Complete `06_rework_02_TZ.md`. This is a narrow contract/test-discipline pass; the core period calculation must not be rewritten.
