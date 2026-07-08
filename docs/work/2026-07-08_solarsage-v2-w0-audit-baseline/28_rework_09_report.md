# Rework 09 Report: Wave W0 SolarSage V2 Audit Baseline

## Changed Files
- `apps/api/tests/test_natal_report_service.py` — Added explicit `retrograde=False` to all `NatalChartPlanet(...)` fixtures
- `apps/api/tests/test_natal_context_service.py` — Added `retrograde` to sidecar validation fixtures
- `apps/api/tests/test_astronomy_oracle.py` — Fixed `resolve_audit_output_dirs` import path for `apps/api` cwd
- `scripts/audit_today.py` — Cleaned up duplicate/unused imports (`NamedTuple`, `field` removed)
- `docs/work/*/26_rework_08_review.md` — Trailing blank line removed
- `docs/work/*/27_rework_09_TZ.md` — Trailing blank line removed

## Root Cause Summary

The W0 retrograde hardening made `NatalChartPlanet.retrograde` and `NatalPreviewChartPlanet.retrograde` required fields. Old test fixtures omitted `retrograde`, causing `ValidationError` during setup. Similarly, sidecar validation tests used planet dicts without `retrograde` or `speed`, triggering the strict validator.

## Fixes Applied

### 1. `test_natal_report_service.py` fixtures
All 16 `NatalChartPlanet(...)` calls now include explicit `retrograde=False` (or preserved `retrograde=True` for Mars). Added via targeted regex replacement.

### 2. `test_natal_context_service.py` sidecar validation
Three test cases updated:
- `test_solar_sage_natal_rejects_empty_houses`: added `retrograde=False` to the Sun planet so the test reaches the intended "empty houses" validation
- `test_solar_sage_natal_accepts_valid_response`: added `retrograde=False` to the Sun planet
- `test_solar_sage_transits_accepts_valid_response`: added `retrograde=False` to the Sun planet

### 3. `test_astronomy_oracle.py` import path
Added `sys.path.insert(0, str(repo_root))` before `from scripts.audit_today import resolve_audit_output_dirs`, so the tests pass from the canonical `apps/api` cwd.

### 4. `scripts/audit_today.py` imports
Removed unused `NamedTuple` and `field` imports. Deduplicated `Any`.

## Verification Results

| Command | Result |
|---|---|
| `cd apps/api && python -m pytest tests/ -q` | **649 passed, 5 skipped** (100% green) |
| W0-specific pytest (6 files) | **43 passed** |
| Sidecar pytest | **5 passed** |
| `scripts/test_audit_scoring_oracle.py` | **exit 0** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| Live sample + `git diff --exit-code` | **Isolated** |
| `rg` gate (N/A/fallback/relationship text) | **Exit 1 (no matches)** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Commit SHA
- **Implementation commit**: `e920420e9e9f32c205ef80fe8281b312963bf836`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
