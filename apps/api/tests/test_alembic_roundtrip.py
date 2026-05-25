"""Alembic round-trip test: upgrade head -> downgrade base -> upgrade head."""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1]


def _run(args: list[str], db_path: Path) -> None:
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    subprocess.run(
        ["alembic", *args],
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
