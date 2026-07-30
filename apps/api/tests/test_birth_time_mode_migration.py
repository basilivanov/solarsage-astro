# ############################################################################
# AI_HEADER: MODULE_TESTS_BIRTH_TIME_MODE_MIGRATION — migration contract tests.
# ROLE: Proves the birth-time mode persistence migration is deterministic,
#       reversible, and fail-closed for invalid enum-like values.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BIRTH-TIME-MODE-MIGRATION
# purpose: Exercise Alembic 0027 against SQLite, including legacy backfill,
#   defaults for raw and ORM-created rows, constraints, downgrade preservation,
#   and deterministic re-upgrade.
# owns:
#   - apps/api/tests/test_birth_time_mode_migration.py
# inputs: Temporary SQLite database and Alembic migration chain through 0026.
# outputs: Assertions over user_profiles schema, data, defaults, and constraints.
# dependencies:
#   - Alembic migration chain
#   - app.db.models.User and UserProfile
#   - sqlite3 and SQLAlchemy
# side_effects: Creates and migrates temporary SQLite database files.
# emitted_logs: none
# invariants:
#   - Existing exact birth_time backfills to exact with no prompt dismissal.
#   - Existing NULL birth_time backfills to unknown with prompt dismissal.
#   - New raw and ORM rows default to unknown, NULL bucket, and false dismissal.
#   - Invalid mode and bucket values are rejected by database constraints.
#   - Downgrade preserves legacy profile data and re-upgrade repeats the backfill.
# failure_policy: Raise assertion or subprocess errors on migration drift.
# END_MODULE_CONTRACT: M-TESTS-BIRTH-TIME-MODE-MIGRATION

# START_MODULE_MAP: M-TESTS-BIRTH-TIME-MODE-MIGRATION
# public_entrypoints:
#   - test_birth_time_mode_migration_round_trip
# semantic_blocks:
#   - LEGACY_BACKFILL: verify exact/null migration semantics
#   - NEW_ROW_DEFAULTS: verify raw and ORM defaults
#   - ENUM_GUARDS: verify mode and bucket fail closed
#   - DOWNGRADE_REUPGRADE: verify preservation and deterministic replay
# owned_tests:
#   - apps/api/tests/test_birth_time_mode_migration.py
# END_MODULE_MAP: M-TESTS-BIRTH-TIME-MODE-MIGRATION

from __future__ import annotations

import os
import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db.models import User, UserProfile


API_DIR = Path(__file__).resolve().parents[1]


# START_BLOCK: ALEMBIC_RUNNER
def _run_alembic(args: list[str], db_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-BIRTH-TIME-MODE-MIGRATION.run_alembic
    # purpose: Run one Alembic command against an isolated SQLite database.
    # inputs: args — Alembic subcommand arguments; db_path — SQLite file path.
    # returns: None after a successful subprocess.
    # side_effects: Creates or mutates the temporary database schema.
    # emitted_logs: none
    # error_behavior: subprocess failure propagates with captured migration output.
    # END_FUNCTION_CONTRACT: F-M-TESTS-BIRTH-TIME-MODE-MIGRATION.run_alembic
    env = os.environ.copy()
    env["DATABASE_URL"] = f"sqlite+aiosqlite:///{db_path}"
    subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=API_DIR,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


# END_BLOCK: ALEMBIC_RUNNER


# START_BLOCK: MIGRATION_ROUND_TRIP
def test_birth_time_mode_migration_round_trip(tmp_path: Path) -> None:
    # START_FUNCTION_CONTRACT: F-M-TESTS-BIRTH-TIME-MODE-MIGRATION.round_trip
    # purpose: Prove 0027 backfills legacy rows, applies new-row defaults,
    #   rejects invalid enum values, preserves legacy data on downgrade, and
    #   deterministically reproduces the backfill after re-upgrade.
    # inputs: tmp_path — isolated test directory.
    # returns: None; assertions raise on migration contract violations.
    # side_effects: Runs Alembic and writes a temporary SQLite database.
    # emitted_logs: none
    # error_behavior: AssertionError or sqlite3.IntegrityError on contract drift.
    # END_FUNCTION_CONTRACT: F-M-TESTS-BIRTH-TIME-MODE-MIGRATION.round_trip
    db_path = tmp_path / "birth-time-mode.db"
    _run_alembic(["upgrade", "0026_day_score_history"], db_path)

    exact_id = "11111111-1111-1111-1111-111111111111"
    unknown_id = "22222222-2222-2222-2222-222222222222"
    raw_new_id = "33333333-3333-3333-3333-333333333333"
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO users (id, tg_user_id) VALUES (?, ?)",
        (exact_id, 1001),
    )
    conn.execute(
        "INSERT INTO users (id, tg_user_id) VALUES (?, ?)",
        (unknown_id, 1002),
    )
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, birth_time, birth_city, current_city)
        VALUES (?, ?, ?, ?)
        """,
        (exact_id, "12:30:00", "Exact City", "Current Exact"),
    )
    conn.execute(
        """
        INSERT INTO user_profiles (user_id, birth_time, birth_city, current_city)
        VALUES (?, ?, ?, ?)
        """,
        (unknown_id, None, "Unknown City", "Current Unknown"),
    )
    conn.commit()
    conn.close()

    _run_alembic(["upgrade", "head"], db_path)

    conn = sqlite3.connect(db_path)
    columns = {
        row[1]: row for row in conn.execute("PRAGMA table_info(user_profiles)")
    }
    assert {"birth_time_mode", "birth_time_bucket", "birth_time_prompt_dismissed"} <= set(columns)
    assert columns["birth_time_mode"][3] == 1
    assert columns["birth_time_prompt_dismissed"][3] == 1

    rows = conn.execute(
        """
        SELECT user_id, birth_time, birth_city, current_city,
               birth_time_mode, birth_time_bucket, birth_time_prompt_dismissed
        FROM user_profiles
        ORDER BY user_id
        """
    ).fetchall()
    assert rows[0][0] == exact_id
    assert rows[0][1] is not None
    assert rows[0][2:] == ("Exact City", "Current Exact", "exact", None, 0)
    assert rows[1][0] == unknown_id
    assert rows[1][1] is None
    assert rows[1][2:] == ("Unknown City", "Current Unknown", "unknown", None, 1)

    conn.execute(
        "INSERT INTO users (id, tg_user_id) VALUES (?, ?)",
        (raw_new_id, 1003),
    )
    conn.execute(
        "INSERT INTO user_profiles (user_id) VALUES (?)",
        (raw_new_id,),
    )
    conn.commit()
    raw_defaults = conn.execute(
        """
        SELECT birth_time_mode, birth_time_bucket, birth_time_prompt_dismissed
        FROM user_profiles WHERE user_id = ?
        """,
        (raw_new_id,),
    ).fetchone()
    assert raw_defaults == ("unknown", None, 0)

    for user_id, tg_user_id, mode, bucket in (
        ("44444444-4444-4444-4444-444444444444", 1004, "invalid", None),
        ("55555555-5555-5555-5555-555555555555", 1005, "unknown", "afternoon"),
    ):
        conn.execute(
            "INSERT INTO users (id, tg_user_id) VALUES (?, ?)",
            (user_id, tg_user_id),
        )
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                """
                INSERT INTO user_profiles (
                    user_id, birth_time_mode, birth_time_bucket
                ) VALUES (?, ?, ?)
                """,
                (user_id, mode, bucket),
            )
        conn.rollback()

    conn.close()

    engine = create_engine(f"sqlite:///{db_path}")
    with Session(engine) as session:
        orm_user = User(tg_user_id=1006)
        orm_user.profile = UserProfile()
        session.add(orm_user)
        session.commit()
        assert orm_user.profile.birth_time_mode == "unknown"
        assert orm_user.profile.birth_time_bucket is None
        assert orm_user.profile.birth_time_prompt_dismissed is False
    engine.dispose()

    _run_alembic(["downgrade", "0026_day_score_history"], db_path)
    conn = sqlite3.connect(db_path)
    column_names = {
        row[1] for row in conn.execute("PRAGMA table_info(user_profiles)")
    }
    assert not {
        "birth_time_mode",
        "birth_time_bucket",
        "birth_time_prompt_dismissed",
    } & column_names
    preserved = conn.execute(
        """
        SELECT user_id, birth_time, birth_city, current_city
        FROM user_profiles WHERE user_id IN (?, ?)
        ORDER BY user_id
        """,
        (exact_id, unknown_id),
    ).fetchall()
    assert preserved[0][1:] == ("12:30:00", "Exact City", "Current Exact")
    assert preserved[1][1:] == (None, "Unknown City", "Current Unknown")
    conn.close()

    _run_alembic(["upgrade", "head"], db_path)
    conn = sqlite3.connect(db_path)
    replayed = conn.execute(
        """
        SELECT birth_time_mode, birth_time_bucket, birth_time_prompt_dismissed
        FROM user_profiles WHERE user_id IN (?, ?)
        ORDER BY user_id
        """,
        (exact_id, unknown_id),
    ).fetchall()
    assert replayed == [("exact", None, 0), ("unknown", None, 1)]
    conn.close()


# END_BLOCK: MIGRATION_ROUND_TRIP
