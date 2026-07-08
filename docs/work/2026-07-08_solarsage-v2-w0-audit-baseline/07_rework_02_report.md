# Rework 02 Report: Wave W0 SolarSage V2 Audit Baseline

## Resolved Findings

### P0 — Scoring oracle can still exit 0 when top_signals mismatch
- **Resolution**: Added `or not comp["top_signals"]["pass"]` to the failure propagation logic in `scripts/audit_scoring_oracle.py::main()`.
- **Regression test**: Added `test_scoring_oracle_top_signals_mismatch_exits_non_zero` that runs the oracle on a valid signal, produces matching day_status & sphere_scores, but injects a completely different top_signals list. Asserts non-zero exit code.

### P1 — Audit claim report is still hardcoded and stale
- **Resolution**: Replaced the hardcoded Basil-specific table in `scripts/audit_today.py` with a fully dynamic `14_claims_audit.md` generator that extracts actual `headline`, `dayStatus`, `moon_phase` fact title, `topFlags`, and the full `ConcreteAdvice` table directly from the generated `TodayPayload`. The pre-fix Basil historical issues are preserved as a clearly labeled `Historical Snapshot` section underneath the dynamic excerpts.

### P1 — Audit docs contradict current W0 artifact contract
- **Resolution**: Fixed `docs/audits/README.md` count from "18" to "16" canonical root files and documented the optional `debug/` subdirectory.
- **Resolution**: Updated `docs/audits/2026-07-08-solarsage-independent-audit.md` title to explicitly say `[HISTORICAL PRE-FIX SNAPSHOT]` with a note explaining pre-fix state vs post-W0 state.

### P1 — Remaining silent retrograde defaults in API/cache chart schemas
- **Resolution**: Removed `= False` defaults from `NatalPreviewChartPlanet.retrograde` and `NatalChartPlanet.retrograde` in `apps/api/app/schemas/natal.py`. Both are now required `retrograde: bool`, so any omission triggers a Pydantic `ValidationError`.
- **Regression test**: Added `test_natal_chart_planet_requires_retrograde` in `apps/api/tests/test_astronomy_oracle.py` that proves both schemas raise `ValidationError` when `retrograde` is omitted.

### P2 — Clean tracked worktree
- **Resolution**: All tracked files are committed. `git status` shows only known unrelated untracked files (`.grace/`, `grace.db`, `skills/`, `docs/superpowers/`).

## Verification Results

| Command | Result |
|---|---|
| `apps/api/.venv/bin/python -m pytest apps/api/tests/test_astronomy_oracle.py ...` | **36 passed** |
| `cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py ...` | **5 passed** |
| `apps/api/.venv/bin/python scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `make audit-day USER_ID=eb3876be-e1b4-43d6-b887-1f8554e33150 DATE=2026-07-08` | **day_status pass=true, sphere_scores pass=true, top_signals pass=true, retrograde_flag_pass=true, moon_phase.pass=true, production_percent=44, content_version=6, cached=false** |
| `git show --check HEAD` | **Clean** (no output) |
| `git status --short --branch` | Only known unrelated untracked files remain |

## Commit SHA
- **Implementation commit**: `a8767392e811121eacfdf75dc99f379269872f19`
- **Report commit**: Committed as a separate commit immediately after the implementation commit, so the implementation SHA is stable and the report does not contain its own commit ID.
