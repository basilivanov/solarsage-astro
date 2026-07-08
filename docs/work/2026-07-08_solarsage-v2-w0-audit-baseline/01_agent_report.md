# Agent Report: Wave W0 SolarSage V2 Audit Baseline + P0 Trust Fixes

## Changed Files
- `Makefile`: Added the `audit-day` target.
- `scripts/audit_today.py`: Updated to write the 16 canonical numbered files (prefixed with `00_` through `15_`) and generate the two markdown reports (`14_claims_audit.md` and `15_audit_summary.md`).
- `apps/solarsage/solarsage/schemas/natal.py`: Added the `retrograde` field to the Pydantic `Planet` model.
- `apps/solarsage/solarsage/utils/ephemeris.py`: Populated `retrograde` flag using `speed_lon < 0` during planet position calculations.
- `apps/api/app/services/today_interpretation_service.py`:
  - Updated the Moon phase calculation inside `build` to use the correct astronomical illumination percentage formula: `(1 - cos(radians(moon_lon - sun_lon))) / 2 * 100`.
  - Added an advice consistency guard inside `validate_row_text` to prevent positive recommendations from contradicting the `"avoid"` row verdict (especially for `relationships`).
  - Adjusted `aspect_evidence` to format the aspect title using English frame-preserving labels (e.g. `Transit Moon opposition natal Pluto`).
- `apps/api/app/services/semantic_service.py`:
  - Updated `build_why_contexts` signature to accept `day_scored_signals`, `natal_background_signals`, and `activation_layer` with clean fallbacks.
  - Adjusted `signal_lines` and contexts to format aspect debug/explanation strings in English and preserve the frame (Transit vs natal) to prevent ambiguity.
  - Filtered `manifestation_zones` (07) and `period_background` (04) contexts to use `transit_houses` instead of `houses` to prevent static natal house signal contamination.
- `apps/api/app/services/today_service.py`: Adjusted `build_why_contexts` invocation to pass `all_signals`, `day_scored_signals`, `natal_background_signals`, and `activation_layer` explicitly.
- `docs/audits/README.md`: Added instructions on how to run and interpret the daily audit.

## Satisfied W0 Requirements
1. **Audit Target**: `make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08` works cleanly and runs both independent scoring and astronomy oracles.
2. **README**: Written `docs/audits/README.md` explaining the audit workflow and artifact meanings.
3. **Artifacts**: Generated the 16 canonical numbered files under `artifacts/audit/2026-07-08/`.
4. **Retrograde Flags**: Solved the retrograde flags bug. Sidecar now returns correct values, and API validates them. (Mercury, Neptune, Pluto are correctly identified as retrograde on 2026-07-08).
5. **Moon Phase**: Replaced the triangular approximation in `TodayInterpretationService.build` with the correct astronomical illumination formula. Moon phase now aligns with the Swiss Ephemeris oracle at `43.792%` (within `0.5pp` tolerance).
6. **Aspect Frame Preservation**: Formatted aspect evidence titles and debug strings in English with explicit frames (e.g. `Transit Moon opposition natal Pluto` and `Transit Moon opposition Transit Pluto`), removing ambiguity.
7. **build_why_contexts Separation**: Cleanly separated `all_signals`, `day_scored_signals`, and `natal_background_signals` in the context builders.
8. **Natal House Contamination**: Manifestation zones and period background contexts now extract only current-day transit house placements.
9. **Advice Consistency Guard**: Implemented and tested the row verdict vs LLM text consistency check.

## Verification Commands Executed
1. **Pytest (API astronomy/semantic/advice/endpoints tests)**:
   ```bash
   apps/api/.venv/bin/python -m pytest \
     apps/api/tests/test_astronomy_oracle.py \
     apps/api/tests/test_semantic_contexts.py \
     apps/api/tests/test_today_concrete_advice_consistency.py \
     apps/api/tests/test_today_concrete_advice.py \
     apps/api/tests/test_day_endpoints.py \
     apps/api/tests/test_calendar_endpoints.py \
     -q
   ```
   **Result**: `30 passed` (100% green, 1.57s).
2. **Pytest (Scoring Oracle tests)**:
   ```bash
   apps/api/.venv/bin/python -m pytest scripts/test_audit_scoring_oracle.py
   ```
   **Result**: `1 passed` (100% green, 0.03s).
3. **Make Audit-Day**:
   ```bash
   make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
   ```
   **Result**: Success. Generated 16 prefixed files and 18 total files under `artifacts/audit/2026-07-08/`.

## Scoring Oracle Comparison Summary
- **Day Status**: Production (`supportive`) matches Oracle (`supportive`).
- **Sphere Scores**: Exact match (delta `0.00`) across all 9 spheres:
  - `crisis_transformation_control`: 5.26
  - `inner_background_unconscious`: 4.45
  - `body_energy_health`: 3.79
  - `work_status_achievement`: 3.46
  - `money_security_resources`: 2.54
  - `home_family_roots`: 1.97
  - `thinking_speech_learning`: 1.42
  - `relationships_partnership`: 0.89
  - `meaning_expansion_vector`: 0.46
- **Top Signals**: Matches perfectly (delta `0.00`).

## Astronomy Oracle Summary
- **Transit Coordinates**: Longitude delta `0.0°` (PASS).
- **Zodiac Signs**: 100% matches (PASS).
- **House Placements**: 100% matches under `WHOLE_SIGN` (PASS).
- **Retrograde Flags**: 100% matches (PASS).
- **Moon Phase**: Swiss formula `43.792%` vs production payload `43.792%` (PASS, within `0.5pp` tolerance).

## Known Limitations / Follow-Up Items for W1+
- The `activation_layer` is currently not implemented in the day/natal pipeline. It remains `None` as expected for W0.
- Technique tracking (firdaria, profections, solar returns, etc.) is not implemented yet. All transits are grouped as `"transit"`.
- Anti-dominance and jsonschema YAML loaders are planned for W3-W5.

## Commit SHA
- **Commit**: `56f66535ff5f082b089409ddeec998bfcaf46791`
