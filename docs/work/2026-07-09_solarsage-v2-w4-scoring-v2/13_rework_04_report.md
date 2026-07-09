# Rework 04 Report — Wave W4 Scoring V2

## Summary

Fixed audit CLI runtime detection: `_ensure_api_runtime()` now tests a real API dependency (`AstroSignal`), not just `import app`. Both `python3 scripts/audit_scoring_v2.py ...` and `PYTHONPATH=... python3 scripts/audit_scoring_v2.py ...` now re-exec into the API venv correctly.

## Changed Files

| File | Change |
|------|--------|
| `scripts/audit_scoring_v2.py` | `_ensure_api_runtime()` tests `from app.schemas.normalization import AstroSignal` for real Pydantic 2 proof; uses `AUDIT_EXEC_REEXECED` env-var guard |

## Fix

### P2: Robust runtime detection
- Tests `from app.schemas.normalization import AstroSignal` which proves Pydantic 2 dependencies are available
- Uses `AUDIT_EXEC_REEXECED` env var (set to `"1"` on re-exec) as infinite-loop guard instead of comparing python executable paths (which fail when venv python is symlinked to system python)

## Verification

| Gate | Result |
|------|--------|
| `python3 scripts/audit_scoring_v2.py ...` (repo root) | Exits 0 |
| `PYTHONPATH=... python3 scripts/audit_scoring_v2.py ...` | Exits 0 |
| Artifact validation (both outputs) | Passed (snake_case, scoring_version, sphere_scores) |
| V2 tests | 22 passed |
| Whitespace | clean |
| Working tree | Clean (except pre-existing untracked) |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
