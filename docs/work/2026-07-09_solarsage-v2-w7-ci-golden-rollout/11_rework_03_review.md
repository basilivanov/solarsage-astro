# W7 Rework 03 Architect Review

Status: REWORK REQUIRED
Reviewed range: 320ef30..bee7319
Date: 2026-07-09

## Findings

### P0 - `python3` performance and rollout gates still fail

Evidence:

```bash
python3 scripts/check_v2_performance_budgets.py
```

Still fails with:

```text
ModuleNotFoundError: No module named 'pydantic.alias_generators'
```

```bash
python3 scripts/check_solarsage_v2_rollout_gates.py
```

Still fails because the rollout gate invokes the performance checker and receives the same error.

Root cause:

```bash
python3 - <<'PY'
import sys
from pathlib import Path
print(Path(sys.executable).resolve())
print(Path('apps/api/.venv/bin/python').resolve())
print(Path(sys.executable).resolve() == Path('apps/api/.venv/bin/python').resolve())
PY
```

prints:

```text
/usr/bin/python3.12
/usr/bin/python3.12
True
```

`apps/api/.venv/bin/python` is a symlink to the system binary. Comparing resolved binaries incorrectly treats system `python3` as equivalent to the API venv Python, so the re-exec is skipped and the script imports with the wrong site-packages.

Control check:

```bash
apps/api/.venv/bin/python scripts/check_v2_performance_budgets.py
```

passes, proving the failure is interpreter context selection, not app logic.

Required fix:

- Do not compare resolved binary targets for venv detection.
- Detect whether the current process is actually running inside `apps/api/.venv`.
- Acceptable signals:
  - `Path(sys.prefix).resolve() == api_venv.resolve()`, or
  - `Path(os.environ.get("VIRTUAL_ENV", "")).resolve() == api_venv.resolve()`, or
  - compare `Path(sys.executable)` against the venv executable path without resolving through the symlink target.
- If not inside the API venv and `apps/api/.venv/bin/python` exists, re-exec through that path.
- Preserve CLI args and keep a recursion guard.
- Add a small self-check or test/verification snippet in the report proving `python3` now re-execs despite the symlink target.

### P1 - Rework 03 report is not committed

Evidence:

```text
?? docs/work/2026-07-09_solarsage-v2-w7-ci-golden-rollout/10_rework_03_report.md
```

Impact:

- The work protocol expects reports under `docs/work` to be durable.
- Architect review had to read an untracked file.

Required fix:

- Include the Rework 04 report in the next commit.
- Leave the existing Rework 03 report intact as audit evidence.

### P2 - Do not use `sudo`

Evidence:

The tmux pane shows a `sudo python3 -c ...` cleanup attempt during Rework 03.

Impact:

- The TZ explicitly said: "Do not use `sudo`."
- This is a process violation even though the command appears not to have changed file ownership.

Required fix:

- Do not use `sudo` in Rework 04.
- If permissions block a file, stop and report the blocker.

## Current Accepted Parts

- The intended bootstrap placement is correct: before app imports.
- `apps/api/.venv/bin/python scripts/check_v2_performance_budgets.py` passes.
- `python3 scripts/check_audit_golden.py` passes.
- The change is scoped to gate scripts, which is the right scope.
