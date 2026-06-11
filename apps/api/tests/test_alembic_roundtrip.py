
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ALEMBIC_ROUNDTRIP
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for alembic_roundtrip.py behavior
# owns:
#   - apps/api/tests/test_alembic_roundtrip.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules
# side_effects: n/a (tests)
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
"""Alembic round-trip test: upgrade head -> downgrade base -> upgrade head."""
from __future__ import annotations

import os
import sys
import subprocess
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]


def _run(args: list[str], db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_DIR,
        env=env,
        check=True,
        capture_output=True,
    )


def test_alembic_round_trip(tmp_path: Path) -> None:
    db = tmp_path / "rt.db"
    _run(["upgrade", "head"], db)
    _run(["downgrade", "base"], db)
    _run(["upgrade", "head"], db)
