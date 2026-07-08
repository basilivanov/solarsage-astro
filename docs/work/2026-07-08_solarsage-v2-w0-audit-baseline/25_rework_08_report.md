# Rework 08 Report: Wave W0 SolarSage V2 Audit Baseline

## Changed Files
- `scripts/audit_today.py` — Factored `resolve_audit_output_dirs()` pure helper; updated `run_audit` to use it
- `apps/api/tests/test_astronomy_oracle.py` — Added pure unit tests for helper; strengthened live isolation test

## Changes

### Pure helper factored
Added `AuditOutputDirs` dataclass and `resolve_audit_output_dirs(out_dir, is_live, timestamp)` pure function to `scripts/audit_today.py`. This function resolves output paths without creating directories or accessing filesystem state, making it fully testable without sidecar/DB.

### Live isolation test strengthened
The existing `test_audit_live_isolates_output` was hardened to:
- Fail when the live audit subprocess exits non-zero (detects live execution regression)
- Assert no canonical root `debug/` directory exists after live mode
- Assert no `00_*` through `15_*` files appear outside `live/<timestamp>/`
- Assert live output exists inside `live/<timestamp>/`

### Pure helper unit tests added
Two new deterministic unit tests for `resolve_audit_output_dirs`:
- `test_audit_resolve_output_dirs_default`: default mode → `root_dir == out_dir`, `debug_dir == out_dir/debug`, not live
- `test_audit_resolve_output_dirs_live`: live mode → `root_dir == out_dir/live/<timestamp>`, `debug_dir == root_dir/debug`, `debug_dir != out_dir/debug`, is live

## Verification Results

| Command | Result |
|---|---|
| `pytest` (full API suite) | **43 passed** |
| `make audit-day` + `git diff --exit-code` | **Deterministic** |
| Live sample + `git diff --exit-code` | **Isolated (zero diff, no restoration)** |
| `rg` gate (N/A/fallback/relationship text) | **Exit 1 (no matches)** |
| `git diff 2f9173f..HEAD --check` | **Clean** |
| `git show --check HEAD` | **Clean** |
| `git status --short --branch` | Only known unrelated untracked files |

## Commit SHA
- **Implementation commit**: `fea4c7668c35925a4a4c589a7dd1b7a7b7e8f6ee`

## Push/Deploy Status
- **Push**: NOT_ATTEMPTED
