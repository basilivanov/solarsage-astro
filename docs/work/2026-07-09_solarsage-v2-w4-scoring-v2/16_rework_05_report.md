# Rework 05 Report — Wave W4 Scoring V2

## Summary

Fixed P1 audit bootstrap: venv interpreter path is no longer `.resolve()`d, preserving the virtualenv symlink so `pyvenv.cfg` is found by Python, enabling Pydantic 2 imports.

## Changed Files

| File | Change |
|------|--------|
| `scripts/audit_scoring_v2.py` | `_ensure_api_runtime()` preserves unresolved `.venv/bin/python` path; uses `sys.prefix` comparison for loop guard |

## Fix

### P1: Preserve venv entry path
- `venv_python = venv_root / "bin" / "python"` (unresolved, keeping the venv symlink)
- `os.execve(str(venv_python), ...)` — symlink chain leads to `pyvenv.cfg` discovery
- `sys.prefix` comparison (`Path(sys.prefix).resolve() == venv_root.resolve()`) replaces broken `.resolve()` symlink comparison
- If import fails while already in the venv or after re-exec, the exception propagates normally (no silent continuation)

## Verification

| Gate | Result |
|------|--------|
| `python3 scripts/audit_scoring_v2.py ...` | Exits 0 |
| `PYTHONPATH=... python3 scripts/audit_scoring_v2.py ...` | Exits 0 |
| Artifact validation (both outputs) | Passed |
| V2 tests | 22 passed |
| Whitespace | clean |
| Working tree | Clean (except pre-existing untracked) |

## Commit

`<commit_sha>`

## Push Status

`NOT_ATTEMPTED`
