# SolarSage Today Payload Audits

This directory contains independent audits and baseline tools for the SolarSage V2 scoring and astronomy calculations.

## How to Run the Audit

Audit modes are explicit. Bare `make audit-day` fails fast and does **not** silently use a frozen baseline.

### Live production proof

```bash
make audit-day-live USER_ID=<user_uuid> DATE=<yyyy-mm-dd>
```

- Calls `TodayService.get_today_payload()`
- Writes `artifact_source.json` with `final_payload_source=TodayService.get_today_payload`
- Prefers sidecar full activation layer for `16_activation_layer.json`
- Live samples may write under `artifacts/audit/<DATE>/live/<timestamp>/`

### Frozen baseline validation

```bash
make audit-day-freeze USER_ID=<user_uuid> DATE=<yyyy-mm-dd>
```

- Requires existing `11_final_today_payload.json`
- Labels the run as `committed_baseline_fixture`
- Is deterministic fixture validation, **not** a fresh production payload proof

Example:

```bash
make audit-day-live USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
make audit-day-freeze USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

`scripts/audit_today.py` always records provenance in `artifact_source.json`:
1. Queries the database for the user profile.
2. Calls the SolarSage sidecar for transits at 12:00.
3. Fetches and validates the sidecar activation layer when available.
4. Performs normalization and filters signals.
5. Performs scoring (sphere scores and top signals).
6. Computes semantic contexts for LLM.
7. In live mode, calls `TodayService` for the final TodayPayload.
8. Executes the independent scoring and astronomy oracles.
9. Outputs numbered JSON/CSV/Markdown artifacts and debug intermediates.

## How to Interpret the Audit Artifacts

Directly under `artifacts/audit/<DATE>/`, you will find the 16 canonical files:

- **`00_input_profile.json`**: The input user profile details (birth date, time, location, tz, current tz).
- **`01_raw_natal_context.json`**: The validated raw natal chart context returned by sidecar/cache.
- **`02_raw_transits.json`**: The validated raw transits returned by the sidecar.
- **`03_normalized_signals_all.json`**: List of all normalized signals before filtering out static natal signals.
- **`04_day_scored_signals_after_filter.csv`**: CSV of transit/day signals that actually go into scoring.
- **`05_signal_trace.csv`**: Full CSV trace of all normalized signals.
- **`06_scoring_intermediate_table.csv`**: Intermediate calculation details (weights, thresholds, modifiers, contributions).
- **`07_sphere_scores.csv` / `08_top_signals.csv`**: Final production scoring outputs.
- **`09_semantic_layer.json` / `10_why_contexts.json`**: The computed semantic themes and LLM prompt contexts.
- **`11_final_today_payload.json`**: The actual `TodayPayload` response returned to the client.
- **`12_scoring_oracle_comparison.json`**: Tolerance comparison of sphere scores and day status between production and independent scoring oracle.
- **`13_astronomy_oracle_summary.json`**: Comparison of planet coordinates, retrograde flags, moon phase, and house placements against direct Swiss Ephemeris.
- **`14_claims_audit.md`**: Evaluation of LLM-generated claims against mathematical astrological evidence.
- **`15_audit_summary.md`**: Executive summary of the audit findings.
