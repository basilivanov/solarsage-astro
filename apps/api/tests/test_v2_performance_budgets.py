import subprocess
import sys
from pathlib import Path

import pytest

pytestmark = pytest.mark.benchmark


def test_v2_performance_budgets():
    script_path = Path(__file__).resolve().parent.parent.parent.parent / "scripts" / "check_v2_performance_budgets.py"
    assert script_path.exists()

    proc = subprocess.run([sys.executable, str(script_path)], capture_output=True, text=True)
    assert proc.returncode == 0, f"Performance check failed: {proc.stderr}\nStdout: {proc.stdout}"
    assert "mode: fixture" in proc.stdout
    assert "Performance budget check: PASSED" in proc.stdout
