# Agent Report — Wave W3.2 Profection Activations

## Summary

Implemented `annual_profection` and `monthly_profection` in the sidecar activation layer builder. W3.2 activations are emitted alongside accepted W3.1 transit activations when default `techniques=[]` is used. `TodayService` remains unwired (`sidecar_activation_layer=None`).

## Changed Files

| File | Change |
|------|--------|
| `apps/solarsage/solarsage/services/activation_builder.py` | Added `annual_profection`, `monthly_profection` to `SUPPORTED_ORDER`; added sign rulers, profection helpers, activation generation |
| `apps/solarsage/tests/test_profections.py` | **New** — 8 sidecar profection tests |
| `apps/solarsage/tests/test_activation_layer_endpoint.py` | Updated technique assertions to include profections |
| `apps/solarsage/tests/test_activation_transits.py` | Updated allowed techniques and evidence frame checks |
| `apps/api/tests/test_activation_layer_profections.py` | **New** — 4 API boundary tests for profection acceptance |
| `scripts/audit_sidecar_activation.py` | Added `--techniques` option |
| `artifacts/audit/2026-07-08/18_sidecar_activation_layer_w3_2_profections.json` | **New** — W3.2 audit artifact (115 activations: 111 transit + 4 profection) |

## Formula Decisions

### Sign Rulers
Traditional rulers only:
- Aries→MARS, Taurus→VENUS, Gemini→MERCURY, Cancer→MOON, Leo→SUN, Virgo→MERCURY, Libra→VENUS, Scorpio→MARS, Sagittarius→JUPITER, Capricorn→SATURN, Aquarius→SATURN, Pisces→JUPITER

### Annual Profection
`age = completed_years(birth_local_date, target_local_date)` → `annual_house = (age % 12) + 1`

Lord of year = traditional ruler of the sign on the annual house cusp.

### Monthly Profection
Annual year start = most recent birthday on/before target. Count completed monthly anniversaries (day-clamped). `monthly_house = ((annual_house - 1 + completed_month_steps) % 12) + 1`

### Strength
From `grace/canon/activation_rules.v1.yml`: annual=0.75, monthly=0.45.

## Basil Golden Values

| Field | Expected | Actual |
|-------|----------|--------|
| age | 45 | 45 |
| annual_house | 10 | 10 |
| lord_of_year | MARS | MARS |
| annual strength | 0.75 | 0.75 |
| completed_month_steps | 8 | 8 |
| monthly_house | 6 | 6 |
| lord_of_month | JUPITER | JUPITER |
| monthly strength | 0.45 | 0.45 |

## Activation Counts

W3.2 artifact: 115 activations (111 W3.1 transit + 4 W3.2 profection)

## Verification Results

| Gate | Result |
|------|--------|
| `pytest test_profections test_activation_layer_endpoint test_activation_transits test_activation_schema -q` (sidecar) | 28 passed, 1 warning |
| `pytest tests/ -q` (sidecar full) | 49 passed, 1 warning |
| `pytest test_activation_layer_profections test_activation_layer_transits test_activation_layer_contract test_today_meta_versions -q` (API) | 19 passed |
| `pytest tests/ -q` (API full) | 686 passed, 5 skipped, 1 warning |
| `python3 scripts/audit_sidecar_activation.py --techniques ...` | Works ✓ |
| `PYTHONHASHSEED=random` × 3 | All identical ✓ |
| Unsupported W3+ techniques in artifact | None ✓ |
| `sidecar_activation_layer=None` in today_service.py | Still None ✓ |
| `git diff --check` (whitespace) | clean ✓ |

## Commit

`1b7674a`

## Push Status

`NOT_ATTEMPTED`
