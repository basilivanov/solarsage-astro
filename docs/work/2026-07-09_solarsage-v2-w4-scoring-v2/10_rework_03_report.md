# Rework 03 Report — Wave W4 Scoring V2

## Summary

Fixed the last W4 acceptance gap: `python3 scripts/audit_scoring_v2.py ...` now works from repo root by self-reexecuting into the API venv.

## Changed Files

| File | Change |
|------|--------|
| `scripts/audit_scoring_v2.py` | Added `_ensure_api_runtime()` for self-reexec into `apps/api/.venv/bin/python` |

## Fix

### P1: Audit CLI from repo root

The script now checks if `import app` works at the top. If it fails (system python3, no PYTHONPATH), it:
1. Locates `apps/api/.venv/bin/python`
2. Sets PYTHONPATH to include `apps/api/` for `app.*` imports
3. Calls `os.execve()` to re-exec into the venv interpreter
4. If the venv python does not exist, prints a clear error message

After bootstrap, the script runs normally under the API venv.

## Verification

| Gate | Result |
|------|--------|
| `python3 scripts/audit_scoring_v2.py ...` from repo root | Exits 0, writes both artifacts |
| Artifact validation (snake_case, scoring_version) | Passed |
| V2 tests (targeted) | 22 passed |
| `rg` fallback patterns in service | No matches |
| `ss-scoring-2.0` in runtime | No matches |
| Whitespace | clean |
| Working tree | Clean (except pre-existing untracked) |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
