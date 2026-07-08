# Rework 01 Report: Wave W0 SolarSage V2 Audit Baseline + P0 Trust Fixes

## Resolved Findings

### P0 — Audit exits successfully while astronomy oracle fails
- **Resolution**: Bumped `TODAY_CONTENT_VERSION` from `5` to `6` to ensure the production cache is invalidated and fresh payloads are regenerated through the corrected Moon phase calculation pipeline.
- **Rounding**: Switched from truncating `int(illumination)` to nearest integer rounding `int(round(illumination))` in `TodayInterpretationService.build`. Illumination now correctly rounds to `44%` for the `43.792%` Swiss Ephemeris oracle value.
- **Fail Propagation**: Modified `main()` in both `scripts/audit_scoring_oracle.py` and `scripts/audit_astronomy_oracle.py` to check all validation flags and exit with code `1` on any mismatch. `make audit-day` correctly propagates this exit code.
- **Regression Test**: Added `test_scoring_oracle_failure_exits_non_zero` in `apps/api/tests/test_astronomy_oracle.py` to ensure that mismatched oracle runs fail with non-zero exit codes.

### P0 — Retrograde remains silently defaulted to false
- **Resolution**: Removed all default `False` values for the `retrograde` field from the audited sidecar and API schemas (`Planet` in sidecar, `SolarSageTransitPlanet` and `SolarSagePlanetPosition` in API).
- **Calculation**: Both the transit (`calculate_positions`) and natal (`calculate_planets`) paths in the sidecar now compute and return `retrograde = speed < 0` explicitly.
- **Derivation**: Added Pydantic validators on the API schemas to dynamically derive `retrograde` from the `speed` field if the explicit flag is omitted. If both `retrograde` and `speed` are missing, a `ValueError` is raised.
- **Tests**: Added a retrograde calculation unit test `test_ephemeris_retrograde_calculation` in `apps/solarsage/tests/test_ephemeris_retrograde.py` and schema validation tests `test_api_schema_retrograde_validation` in `apps/api/tests/test_astronomy_oracle.py`.

### P0 — Day/natal evidence separation is incomplete
- **Resolution**: Re-implemented `build_why_contexts` in `SemanticService` to authoritatively source transit aspects and houses from `day_scored_signals`.
- **Natal Background**: Configured the `period_background` (04) context to isolate static natal background signals and explicitly label them as `"Натальный фон (индивидуальная база)"`.
- **Tests**: Updated `test_semantic_contexts.py` to assert that both static natal houses and static natal aspects are cleanly separated and never contaminate current-day transit contexts.

### P1 — Advice guard rejects the allowed mitigation from the specification
- **Resolution**: Updated `validate_row_text` to support conditional/mitigation language (e.g. `"если нужно"`, `"только"`, `"короткий формат"`, `"избегай"`, `"не "`).
- **Prompt**: Added a verdict-specific `avoid` rule to the concrete advice generator prompt in `llm_service.py` to guide LLM generation before validation.
- **Tests**: Added the exact specification allowed mitigation example as a passing test case, and verified that active outreach without mitigation under `"avoid"` still fails.

### P1 — Moon phase regression test does not test production behavior
- **Resolution**: Added `test_today_interpretation_service_moon_phase_rounding` in `apps/api/tests/test_astronomy_oracle.py` to build a real `DayChart` and test the actual `TodayInterpretationService.build` method's rounding output.

### P1 — Audit artifact generator is case-hardcoded and root output is duplicated
- **Resolution**: Made reports dynamically generated using actual inputs (`args.user_id`, `args.date`) and computed values. Removed unnumbered legacy duplicates from the root and put them under `debug/`. Kept only the canonical 16 root files.

### P2 — Commit hygiene
- **Whitespace**: Cleaned up all trailing whitespace from modified files.
- **CSV line endings**: Added `lineterminator="\n"` to all CSV DictWriters.
- **git show check**: Verified that `git show --check HEAD` passes cleanly without any whitespace warnings or carriage returns.

## Verification Commands Results
- `apps/api/tests/test_astronomy_oracle.py`, `test_semantic_contexts.py`, `test_today_concrete_advice_consistency.py`, etc. -> **`34 passed`** (100% green).
- `apps/solarsage/tests/test_ephemeris_retrograde.py`, `test_services.py` -> **`5 passed`** (100% green).
- `make audit-day` -> **`Success`** (0 exit code, generated 16 numbered canonical files under `artifacts/audit/2026-07-08/`).
- `git show --check HEAD` -> **`Clean`** (no output).

## Commit SHA
- **Commit**: `42f48f816ea422ceebba5a57702f2d4ecd5f8c5d`
