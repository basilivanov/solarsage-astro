# Rework 03 Report: Wave W0 SolarSage V2 Audit Baseline

## Resolved Findings

### P1 — Dynamic claims report reads camelCase but payload is snake_case
- **Resolution**: Rewrote claims field extraction in `scripts/audit_today.py` with a defensive `_get_field()` helper that tries snake_case keys first, then camelCase as fallback.
- **Regression test**: Added `test_audit_claims_report_has_no_na_placeholders_for_present_data` in `apps/api/tests/test_astronomy_oracle.py` that verifies the generated `14_claims_audit.md` does not contain `"N/A"` placeholders for fields that are populated in the actual payload.
- **Regenerated artifacts**: Ran `make audit-day` to regenerate `14_claims_audit.md` with real data (Moon phase, top flags, all 12 advice rows).

### P2 — Trailing whitespace across the commit range
- **Resolution**: Stripped trailing trailing whitespace from `apps/api/tests/test_astronomy_oracle.py`, `scripts/audit_today.py`, `docs/audits/2026-07-08-solarsage-independent-audit.md`, `docs/work/2026-07-08_solarsage-v2-w0-audit-baseline/05_rework_01_review.md`, and `08_rework_02_review.md`.
- **Verification**: Both `git diff 2f9173f..HEAD --check` and `git show --check HEAD` now pass cleanly.

## Verification Results

| Command | Result |
|---|---|
| `pytest apps/api/tests/test_astronomy_oracle.py ...` | **37 passed** |
| `cd apps/solarsage && venv/bin/python -m pytest tests/test_ephemeris_retrograde.py ...` | **5 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `make audit-day` | **Success** (`content_version=6`, `cached=false`, `moon_phase.pass=true`, `retrograde_flag_pass=true`, `day_status.pass=true`, `top_signals.pass=true`) |
| `rg` for N/A patterns in claims report | **No matches** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files remain |

## Commit SHA
- **Implementation commit**: `6605df523b5e489c62996b3001f11df1bdc00583`
- **Whitespace fix commit**: `3b42fb15c5454bb5b5ecf6d0afce07d0f2f8e24b`
- **Note**: The callback HEAD conveys the actual final SHA; it is not embedded here to avoid self-reference.
