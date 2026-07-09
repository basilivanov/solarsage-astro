#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

def main():
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
        print("Audit golden snapshots gate: FAILED")
        sys.exit(proc.returncode)

    print("Audit golden snapshots gate: PASSED")
    sys.exit(0)

if __name__ == "__main__":
    main()
