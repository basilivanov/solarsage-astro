# SolarSage Today Payload Audits

This directory contains independent audits and baseline tools for the SolarSage V2 scoring and astronomy calculations.

## How to Run the Audit

To collect production inputs, transits, and scoring results for a given user and date, run the following command:

```bash
make audit-day USER_ID=<user_uuid> DATE=<yyyy-mm-dd>
```

For example, to run the baseline audit for user Basil on 2026-07-08:

```bash
make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08
```

This command executes `scripts/audit_today.py` which:
1. Queries the database for the user profile.
2. Calls the SolarSage sidecar for transits at 12:00.
3. Performs normalization and filters signals.
4. Performs scoring (sphere scores and top signals).
5. Computes semantic contexts for LLM.
6. Calls `TodayService` to fetch the final TodayPayload.
7. Executes the independent scoring and astronomy oracles.
8. Outputs 16 canonical numbered JSON, CSV, and Markdown files directly under `artifacts/audit/<DATE>/`, and places intermediate/unprefixed debug logs and oracle details in a `debug/` subdirectory.

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
