# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ALEMBIC_ROUNDTRIP
# ROLE: Module
# DEPENDENCIES: local modules, sqlite3, alembic
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for alembic_roundtrip.py behavior and SQLite schema defaults verification
# owns:
#   - apps/api/tests/test_alembic_roundtrip.py
# inputs: Mocks, fixtures
# outputs: Assertion results
# dependencies: local modules, sqlite3
# side_effects: database migrations execution
# emitted_logs: n/a (tests)
# invariants:
#   - alembic upgrade head -> downgrade base -> upgrade head completes cleanly
#   - SQLite table defaults apply on raw column inserts without explicit defaults
# failure_policy: log and raise
# END_MODULE_CONTRACT
"""Alembic round-trip test: upgrade head -> downgrade base -> upgrade head."""
from __future__ import annotations

import os
import sys
import sqlite3
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

    # SQLite default smoke test: insert promo_campaign without defaulted fields
    conn = sqlite3.connect(db)
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO promo_campaigns (id, display_name, code_hash, activation_starts_at, activation_ends_at, max_redemptions)
        VALUES ('11111111-1111-1111-1111-111111111111', 'Smoke Campaign', 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2', '2026-07-24 00:00:00', '2026-08-24 00:00:00', 100);
        """
    )
    conn.commit()

    cursor.execute(
        "SELECT active, redemptions_used, access_days, bonus_credits, unlock_natal, created_at, updated_at FROM promo_campaigns WHERE id = '11111111-1111-1111-1111-111111111111';"
    )
    row = cursor.fetchone()
    conn.close()

    assert row is not None
    active, redemptions_used, access_days, bonus_credits, unlock_natal, created_at, updated_at = row
    assert active in (1, True)
    assert redemptions_used == 0
    assert access_days == 30
    assert bonus_credits == 50
    assert unlock_natal in (1, True)
    assert created_at is not None
    assert updated_at is not None

    _run(["downgrade", "base"], db)
    _run(["upgrade", "head"], db)
