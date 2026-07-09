#!/usr/bin/env python3
# START_MODULE_CONTRACT: M-AUDIT-GOLDEN-GATE
# purpose: Run offline golden snapshot tests in CI/local to verify scoring/aspect tolerances.
# owns:
#   - scripts/check_audit_golden.py
# inputs: none
# outputs: sys.exit(0) on success, sys.exit(1) on failure
# dependencies: apps/api/tests/test_golden_basil_2026_07_08.py, apps/api/tests/test_golden_v2_convergence.py
# side_effects: runs pytest subprocess
# emitted_logs: system.audit_golden_passed, system.audit_golden_failed
# END_MODULE_CONTRACT: M-AUDIT-GOLDEN-GATE

# START_MODULE_MAP: M-AUDIT-GOLDEN-GATE
# public_entrypoints:
#   - main
# semantic_blocks:
#   - GOLDEN_GATE: runs pytest on golden snapshot tests
# END_MODULE_MAP: M-AUDIT-GOLDEN-GATE

# ############################################################################
# AI_HEADER: TOOL_AUDIT_GOLDEN_GATE
# ROLE: Deterministic offline CI/local gate for scoring V1/V2 golden snapshots.
# DEPENDENCIES: stdlib only, pytest in venv
# ############################################################################

import json
import subprocess
import sys
from pathlib import Path

def log_event(event: str, level: str, msg: str) -> None:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-GOLDEN-GATE.log_event
    # purpose: Emit structured JSON log to stdout.
    # inputs: event (str), level (str), msg (str)
    # returns: None
    # side_effects: writes to stdout
    # END_FUNCTION_CONTRACT: F-M-AUDIT-GOLDEN-GATE.log_event
    from datetime import datetime, UTC
    print(json.dumps({
        "ts": datetime.now(UTC).isoformat() + "Z",
        "level": level,
        "event": event,
        "msg": msg,
        "service": "audit-tool",
        "slice": "W7",
        "module": "M-AUDIT-GOLDEN-GATE",
        "block": "AUDIT_RUN",
    }))

def main() -> None:
    # START_FUNCTION_CONTRACT: F-M-AUDIT-GOLDEN-GATE.main
    # purpose: Main entry point for audit golden snapshots gate.
    # inputs: none
    # returns: None
    # side_effects: runs pytest subprocess, exits process
    # END_FUNCTION_CONTRACT: F-M-AUDIT-GOLDEN-GATE.main
    print("=== Running Audit Golden Snapshots Gate ===")
    api_dir = Path(__file__).resolve().parent.parent / "apps" / "api"
    venv_python = api_dir / ".venv" / "bin" / "python"

    python_exec = str(venv_python) if venv_python.exists() else sys.executable

    cmd = [
        python_exec, "-m", "pytest",
        str(api_dir / "tests" / "test_golden_basil_2026_07_08.py"),
        str(api_dir / "tests" / "test_golden_v2_convergence.py"),
        "-q"
    ]

    proc = subprocess.run(cmd, cwd=str(api_dir))
    if proc.returncode != 0:
        log_event("system.audit_golden_failed", "error", "Audit golden snapshots gate failed")
        print("Audit golden snapshots gate: FAILED")
        sys.exit(proc.returncode)

    log_event("system.audit_golden_passed", "info", "Audit golden snapshots gate passed")
    print("Audit golden snapshots gate: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
