# ############################################################################
# AI_HEADER: TEST_TODAY-CONVERGENCE-SNAPSHOT-SCHEMA — P3-A persistence schema tests.
# ROLE: Proves the additive snapshot/narrative schema and EveningCheckin lineage
#       without exercising any P3-B/C business service behavior.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SNAPSHOT-SCHEMA
# purpose: Exercise Alembic 0028 and ORM metadata against SQLite with foreign
#   keys enabled, preserving the existing EveningCheckin contract.
# owns:
#   - apps/api/tests/test_today_convergence_snapshot_schema.py
# inputs: Isolated SQLite databases, migration revisions, and typed ORM rows.
# outputs: Assertions over columns, constraints, indexes, defaults, FKs, and roundtrips.
# dependencies: Alembic, SQLAlchemy, app.db.models, and migration 0027.
# side_effects: Creates temporary SQLite databases and applies local migrations.
# emitted_logs: none.
# invariants: The migration is additive; legacy check-in uniqueness/streak and
#   pre-existing rows remain intact; no P3-B business invariants are tested.
# failure_policy: Migration/SQLAlchemy errors and constraint violations fail tests.
# END_MODULE_CONTRACT: M-TEST-TODAY-CONVERGENCE-SNAPSHOT-SCHEMA

# START_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SNAPSHOT-SCHEMA
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - MIGRATION_ROUNDTRIP: 0027/head transitions and legacy check-in preservation.
#   - SCHEMA_CONTRACT: columns, nullability, defaults, constraints, indexes, and FKs.
#   - ROW_CONTRACT: valid rows, duplicate/invalid rejection, JSON, timestamps, and lineage.
#   - METADATA_PARITY: ORM table metadata and migration source boundaries.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-CONVERGENCE-SNAPSHOT-SCHEMA

from __future__ import annotations

import json
import os
import sqlite3
import subprocess
import sys
import uuid
from datetime import date
from pathlib import Path

import pytest
from sqlalchemy import create_engine, event, inspect
from sqlalchemy.orm import Session

from app.db.models import EveningCheckin, TodaySnapshot, TodaySnapshotNarrative, User


API_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = API_DIR.parents[1]
SNAPSHOT_REVISION = "0028_today_convergence_snapshots"


# START_BLOCK: MIGRATION_ROUNDTRIP
def _run_alembic(args: list[str], db_path: Path) -> None:
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


def _connection(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.execute("PRAGMA foreign_keys=ON")
    connection.create_function("now", 0, lambda: "2026-07-31 12:00:00")
    return connection


def _orm_engine(db_path: Path):
    engine = create_engine(f"sqlite:///{db_path}")

    @event.listens_for(engine, "connect")
    def _register_now(dbapi_connection, _connection_record) -> None:
        dbapi_connection.create_function("now", 0, lambda: "2026-07-31 12:00:00")

    return engine


def _seed_user_and_checkin(connection: sqlite3.Connection) -> tuple[str, int]:
    user_id = uuid.uuid4().hex
    connection.execute("INSERT INTO users (id, tg_user_id) VALUES (?, ?)", (user_id, 930001))
    connection.execute(
        "INSERT INTO evening_checkins (user_id, target_date, mood, streak) VALUES (?, ?, ?, ?)",
        (user_id, "2026-07-31", "good", 7),
    )
    connection.commit()
    row_id = connection.execute(
        "SELECT id FROM evening_checkins WHERE user_id = ?", (user_id,)
    ).fetchone()[0]
    return user_id, row_id


def test_migration_adds_schema_and_roundtrips_without_changing_legacy_checkin(tmp_path: Path) -> None:
    db_path = tmp_path / "schema.db"
    _run_alembic(["upgrade", "0027_birth_time_mode"], db_path)
    connection = _connection(db_path)
    user_id, checkin_id = _seed_user_and_checkin(connection)
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(inspection_engine)
    legacy_checkin_columns = {column["name"] for column in inspector.get_columns("evening_checkins")}

    _run_alembic(["upgrade", "head"], db_path)
    inspection_engine.dispose()
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(inspection_engine)
    checkin_columns = {column["name"] for column in inspector.get_columns("evening_checkins")}
    assert checkin_columns - legacy_checkin_columns == {
        "forecast_snapshot_id",
        "prediction_seen_at",
        "prediction_seen_surface",
        "observed_spheres",
    }
    assert inspector.get_pk_constraint("evening_checkins")["constrained_columns"] == ["id"]
    assert any(
        unique["name"] == "uq_checkin_user_date"
        and unique["column_names"] == ["user_id", "target_date"]
        for unique in inspector.get_unique_constraints("evening_checkins")
    )
    head_table_columns = {
        table_name: tuple(column["name"] for column in inspector.get_columns(table_name))
        for table_name in inspector.get_table_names()
    }
    legacy = connection.execute(
        "SELECT user_id, target_date, mood, streak, forecast_snapshot_id FROM evening_checkins WHERE id = ?",
        (checkin_id,),
    ).fetchone()
    assert legacy == (user_id, "2026-07-31", "good", 7, None)

    _run_alembic(["downgrade", "0027_birth_time_mode"], db_path)
    inspection_engine.dispose()
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(inspection_engine)
    assert not {"today_snapshots", "today_snapshot_narratives"} & set(inspector.get_table_names())
    assert "forecast_snapshot_id" not in {
        column["name"] for column in inspector.get_columns("evening_checkins")
    }
    preserved = connection.execute(
        "SELECT user_id, target_date, mood, streak FROM evening_checkins WHERE id = ?", (checkin_id,)
    ).fetchone()
    assert preserved == (user_id, "2026-07-31", "good", 7)

    _run_alembic(["upgrade", "head"], db_path)
    inspection_engine.dispose()
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    roundtrip_inspector = inspect(inspection_engine)
    roundtrip_table_columns = {
        table_name: tuple(column["name"] for column in roundtrip_inspector.get_columns(table_name))
        for table_name in roundtrip_inspector.get_table_names()
    }
    assert roundtrip_table_columns == head_table_columns
    assert SNAPSHOT_REVISION in subprocess.run(
        [sys.executable, "-m", "alembic", "current"],
        cwd=API_DIR,
        env={**os.environ, "DATABASE_URL": f"sqlite+aiosqlite:///{db_path}"},
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    connection.close()
    inspection_engine.dispose()


# END_BLOCK: MIGRATION_ROUNDTRIP


# START_BLOCK: SCHEMA_CONTRACT
def test_snapshot_narrative_and_lineage_schema_matches_packet_contract(tmp_path: Path) -> None:
    db_path = tmp_path / "schema-contract.db"
    _run_alembic(["upgrade", "head"], db_path)
    connection = _connection(db_path)
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(inspection_engine)

    assert [column["name"] for column in inspector.get_columns("today_snapshots")] == [
        "id", "user_id", "target_date", "timezone", "profile_hash", "input_hash",
        "canon_hash", "formula_version", "calculation_version", "ephemeris_artifact_id",
        "birth_time_mode", "birth_time_range", "deterministic_result_json",
        "canonical_input_json", "created_at", "published_at", "first_day_seen_at",
        "first_lookahead_seen_at", "supersedes_snapshot_id",
    ]
    assert [column["name"] for column in inspector.get_columns("today_snapshot_narratives")] == [
        "id", "snapshot_id", "prompt_version", "status", "content_json", "attempt_count",
        "lease_until", "next_retry_at", "last_error_code", "created_at", "updated_at",
    ]

    columns = {column["name"]: column for column in inspector.get_columns("today_snapshots")}
    assert columns["id"]["nullable"] is False
    assert columns["user_id"]["nullable"] is False
    assert columns["birth_time_range"]["nullable"] is False
    assert columns["deterministic_result_json"]["nullable"] is False
    assert columns["created_at"]["nullable"] is False and columns["created_at"]["default"] is not None
    assert columns["published_at"]["nullable"] is False and columns["published_at"]["default"] is not None
    narrative_columns = {column["name"]: column for column in inspector.get_columns("today_snapshot_narratives")}
    assert narrative_columns["content_json"]["nullable"] is True
    assert narrative_columns["attempt_count"]["nullable"] is False
    assert narrative_columns["attempt_count"]["default"] is not None
    assert narrative_columns["updated_at"]["default"] is not None

    assert {unique["name"] for unique in inspector.get_unique_constraints("today_snapshots")} >= {
        "uq_today_snapshots_identity"
    }
    assert {unique["name"] for unique in inspector.get_unique_constraints("today_snapshot_narratives")} >= {
        "uq_today_snapshot_narratives_version"
    }
    check_names = {
        check["name"] for table in ("today_snapshots", "today_snapshot_narratives", "evening_checkins")
        for check in inspector.get_check_constraints(table)
    }
    assert {
        "ck_today_snapshots_birth_time_mode",
        "ck_today_snapshot_narratives_status",
        "ck_today_snapshot_narratives_attempt_count",
        "ck_evening_checkins_prediction_seen_surface",
    } <= check_names
    index_names = {
        index["name"] for table in ("today_snapshots", "today_snapshot_narratives", "evening_checkins")
        for index in inspector.get_indexes(table)
    }
    assert {
        "ix_today_snapshots_user_date_published",
        "ix_today_snapshots_supersedes_snapshot_id",
        "ix_today_snapshot_narratives_status_retry",
        "ix_evening_checkins_forecast_snapshot_id",
    } <= index_names

    snapshot_fks = {foreign["name"]: foreign for foreign in inspector.get_foreign_keys("today_snapshots")}
    narrative_fks = {foreign["name"]: foreign for foreign in inspector.get_foreign_keys("today_snapshot_narratives")}
    checkin_fks = {foreign["name"]: foreign for foreign in inspector.get_foreign_keys("evening_checkins")}
    assert snapshot_fks["fk_today_snapshots_user_id_users"]["options"]["ondelete"] == "CASCADE"
    assert snapshot_fks["fk_today_snapshots_supersedes_snapshot_id"]["options"]["ondelete"] == "RESTRICT"
    assert narrative_fks["fk_today_snapshot_narratives_snapshot_id"]["options"]["ondelete"] == "CASCADE"
    assert checkin_fks["fk_evening_checkins_forecast_snapshot_id"]["options"]["ondelete"] == "SET NULL"
    connection.close()
    inspection_engine.dispose()


# END_BLOCK: SCHEMA_CONTRACT


# START_BLOCK: ROW_CONTRACT
def test_valid_rows_duplicates_invalid_values_and_lineage_actions(tmp_path: Path) -> None:
    db_path = tmp_path / "rows.db"
    _run_alembic(["upgrade", "head"], db_path)
    connection = _connection(db_path)
    user_id = uuid.uuid4().hex
    snapshot_id = uuid.uuid4().hex
    connection.execute("INSERT INTO users (id, tg_user_id) VALUES (?, ?)", (user_id, 930002))
    connection.execute(
        """
        INSERT INTO today_snapshots (
            id, user_id, target_date, timezone, profile_hash, input_hash, canon_hash,
            formula_version, calculation_version, ephemeris_artifact_id, birth_time_mode,
            birth_time_range, deterministic_result_json, canonical_input_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            snapshot_id, user_id, "2026-07-31", "UTC", "p" * 64, "i" * 64, "c" * 64,
            "today-convergence-2", "ss-calc-1.3.0", "ephemeris-1", "exact",
            json.dumps({"mode": "exact"}), json.dumps({"state": "quiet_day"}), json.dumps(["input"]),
        ),
    )
    connection.execute(
        "INSERT INTO today_snapshot_narratives (id, snapshot_id, prompt_version, status, content_json) VALUES (?, ?, ?, ?, ?)",
        (uuid.uuid4().hex, snapshot_id, "prompt-1", "ready", json.dumps({"text": "ok"})),
    )
    connection.execute(
        "INSERT INTO evening_checkins (user_id, target_date, mood, streak, forecast_snapshot_id, observed_spheres) VALUES (?, ?, ?, ?, ?, ?)",
        (user_id, "2026-07-31", "good", 2, snapshot_id, json.dumps(["work"])),
    )
    connection.commit()

    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            """
            INSERT INTO today_snapshots (
                id, user_id, target_date, timezone, profile_hash, input_hash, canon_hash,
                formula_version, calculation_version, ephemeris_artifact_id, birth_time_mode,
                birth_time_range, deterministic_result_json, canonical_input_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                uuid.uuid4().hex, user_id, "2026-07-31", "UTC", "p" * 64, "i" * 64, "c" * 64,
                "today-convergence-2", "ss-calc-1.3.0", "ephemeris-1", "exact", "{}", "{}", "[]",
            ),
        )
    connection.rollback()
    with pytest.raises(sqlite3.IntegrityError):
        connection.execute(
            "INSERT INTO today_snapshot_narratives (id, snapshot_id, prompt_version, status) VALUES (?, ?, ?, ?)",
            (uuid.uuid4().hex, snapshot_id, "prompt-1", "pending"),
        )
    connection.rollback()
    invalid_rows = (
        ("birth_time_mode", "invalid"),
        ("narrative_status", "broken"),
        ("attempt_count", -1),
        ("prediction_seen_surface", "other"),
    )
    for label, value in invalid_rows:
        with pytest.raises(sqlite3.IntegrityError):
            if label == "birth_time_mode":
                connection.execute(
                    """
                    INSERT INTO today_snapshots (
                        id, user_id, target_date, timezone, profile_hash, input_hash, canon_hash,
                        formula_version, calculation_version, ephemeris_artifact_id, birth_time_mode,
                        birth_time_range, deterministic_result_json, canonical_input_json
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (uuid.uuid4().hex, user_id, "2026-08-01", "UTC", "p" * 64, "i" * 64, "c" * 64, "f", "c", "e", value, "{}", "{}", "{}"),
                )
            elif label == "narrative_status":
                connection.execute(
                    "INSERT INTO today_snapshot_narratives (id, snapshot_id, prompt_version, status) VALUES (?, ?, ?, ?)",
                    (uuid.uuid4().hex, snapshot_id, uuid.uuid4().hex, value),
                )
            elif label == "attempt_count":
                connection.execute(
                    "INSERT INTO today_snapshot_narratives (id, snapshot_id, prompt_version, status, attempt_count) VALUES (?, ?, ?, ?, ?)",
                    (uuid.uuid4().hex, snapshot_id, uuid.uuid4().hex, "pending", value),
                )
            else:
                connection.execute(
                    "INSERT INTO evening_checkins (user_id, target_date, mood, prediction_seen_surface) VALUES (?, ?, ?, ?)",
                    (user_id, "2026-08-01", "good", value),
                )
        connection.rollback()

    connection.execute("DELETE FROM today_snapshots WHERE id = ?", (snapshot_id,))
    connection.commit()
    assert connection.execute("SELECT COUNT(*) FROM today_snapshot_narratives").fetchone()[0] == 0
    assert connection.execute("SELECT forecast_snapshot_id FROM evening_checkins WHERE user_id = ?", (user_id,)).fetchone()[0] is None
    connection.close()

    engine = _orm_engine(db_path)
    with engine.begin() as sql_connection:
        sql_connection.exec_driver_sql("PRAGMA foreign_keys=ON")
    with Session(engine) as session:
        orm_user = User(tg_user_id=930003)
        session.add(orm_user)
        session.flush()
        orm_snapshot = TodaySnapshot(
            user_id=orm_user.id,
            target_date=date(2026, 8, 2),
            timezone="UTC",
            profile_hash="p" * 64,
            input_hash="i" * 64,
            canon_hash="c" * 64,
            formula_version="f",
            calculation_version="c",
            ephemeris_artifact_id="e",
            birth_time_mode="unknown",
            birth_time_range=["00:00", "23:59"],
            deterministic_result_json={"state": "quiet_day"},
            canonical_input_json=["input"],
        )
        session.add(orm_snapshot)
        session.flush()
        session.add(TodaySnapshotNarrative(snapshot_id=orm_snapshot.id, prompt_version="prompt-2", status="pending"))
        session.add(EveningCheckin(user_id=orm_user.id, target_date=date(2026, 8, 2), mood="neutral", forecast_snapshot_id=orm_snapshot.id))
        session.commit()
        assert orm_snapshot.created_at is not None
        assert orm_snapshot.published_at is not None
    engine.dispose()


# END_BLOCK: ROW_CONTRACT


# START_BLOCK: METADATA_PARITY
def test_orm_metadata_matches_new_tables_and_migration_has_no_legacy_today_import(tmp_path: Path) -> None:
    db_path = tmp_path / "metadata.db"
    _run_alembic(["upgrade", "head"], db_path)
    connection = _connection(db_path)
    inspection_engine = create_engine(f"sqlite:///{db_path}")
    inspector = inspect(inspection_engine)
    for table_name in ("today_snapshots", "today_snapshot_narratives", "evening_checkins"):
        assert set(inspector.get_columns(table_name)[index]["name"] for index in range(len(inspector.get_columns(table_name)))) == set(
            TodaySnapshot.__table__.columns.keys() if table_name == "today_snapshots" else
            TodaySnapshotNarrative.__table__.columns.keys() if table_name == "today_snapshot_narratives" else
            EveningCheckin.__table__.columns.keys()
        )
    migration_source = (API_DIR / "alembic/versions/0028_today_convergence_snapshots.py").read_text(encoding="utf-8")
    assert "today_payloads_cache" not in migration_source
    assert "today_service" not in migration_source
    connection.close()
    inspection_engine.dispose()


# END_BLOCK: METADATA_PARITY
