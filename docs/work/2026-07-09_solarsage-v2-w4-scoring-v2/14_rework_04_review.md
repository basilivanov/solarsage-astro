# W4 Rework 04 Architect Review — Rework Required

Status: REWORK REQUIRED
Branch: `main`
Reviewed commits: `e45899e` implementation, `4986823` report finalization
Reviewed report: `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/13_rework_04_report.md`

## Fresh Verification

Targeted W4 tests pass:

```text
22 passed in 0.32s
```

Both required audit CLI modes fail:

```bash
python3 scripts/audit_scoring_v2.py ...
```

and:

```bash
PYTHONPATH=/opt/solarsage-astro/apps/api python3 scripts/audit_scoring_v2.py ...
```

Observed for both:

```text
ModuleNotFoundError: No module named 'pydantic.alias_generators'
```

## Finding

### P1 — resolving the venv interpreter path disables the virtual environment

File: `scripts/audit_scoring_v2.py:54`

Current code:

```python
venv_python = (... / ".venv" / "bin" / "python").resolve()
```

The venv interpreter is a symlink chain:

```text
apps/api/.venv/bin/python -> python3.12
apps/api/.venv/bin/python3.12 -> /usr/bin/python3.12
```

Calling `.resolve()` changes the executable passed to `os.execve()` from the venv entry path to `/usr/bin/python3.12`. Python therefore does not discover `pyvenv.cfg` and runs outside the venv.

Fresh proof:

```text
apps/api/.venv/bin/python:
  executable /opt/solarsage-astro/apps/api/.venv/bin/python
  prefix /opt/solarsage-astro/apps/api/.venv
  base_prefix /usr
  pydantic 2.13.4

/usr/bin/python3.12:
  executable /usr/bin/python3.12
  prefix /usr
  base_prefix /usr
  pydantic 1.10.14
```

The `AUDIT_EXEC_REEXECED=1` guard then prevents another attempt, so the script proceeds under system Python and fails on Pydantic 2 imports.

## Required Next Step

Implement `docs/work/2026-07-09_solarsage-v2-w4-scoring-v2/15_rework_05_TZ.md`.
