# ############################################################################
# AI_HEADER: TEST_CHECKIN-OBSERVED-SPHERES-MIGRATION — persisted check-in sphere data migration.
# ROLE: Proves canonical rename, removal, deduplication, idempotence, and fail-closed unknown handling.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CHECKIN-OBSERVED-SPHERES-MIGRATION
# purpose: Validate the 0031 data migration against an isolated SQLite table.
# owns:
#   - apps/api/tests/test_checkin_observed_spheres_migration.py
# inputs: JSON observed_spheres rows and the Alembic migration module.
# outputs: Canonicalized rows or counted unknown-key failures.
# dependencies: Alembic, SQLAlchemy, migration 0031.
# side_effects: Temporary in-memory SQLite rows only.
# emitted_logs: none.
# invariants: mapping preserves order, deduplicates after aliases, and never
#   guesses unknown values; an empty table and a second run are no-ops.
# failure_policy: assertions fail closed on data loss or partial unknown migration.
# END_MODULE_CONTRACT: M-TEST-CHECKIN-OBSERVED-SPHERES-MIGRATION

# START_MODULE_MAP: M-TEST-CHECKIN-OBSERVED-SPHERES-MIGRATION
# public_entrypoints:
#   - test_mapping_removal_and_deduplication
#   - test_unknown_values_abort_with_occurrence_counts
#   - test_empty_and_second_upgrade_are_noops
# semantic_blocks:
#   - CANONICAL_MAPPING: legacy aliases, removed keys, and ordered deduplication.
#   - FAIL_CLOSED_UNKNOWN: full preflight aborts without partial updates.
#   - IDEMPOTENCE: empty and already-canonical data remain stable.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-CHECKIN-OBSERVED-SPHERES-MIGRATION

from __future__ import annotations

import importlib.util
from collections import Counter
from pathlib import Path
from typing import Any

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import Column, JSON, MetaData, String, Table, create_engine, insert, select


ROOT = Path(__file__).resolve().parents[3]
MIGRATION_PATH = ROOT / "apps/api/alembic/versions/0031_checkin_observed_spheres.py"


def _migration_module() -> Any:
    spec = importlib.util.spec_from_file_location(
        "checkin_observed_spheres_migration", MIGRATION_PATH
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("0031 migration module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _table() -> Table:
    metadata = MetaData()
    return Table(
        "evening_checkins",
        metadata,
        # The migration only needs the existing JSON column and primary key.
        # A compact table keeps these tests independent of the full ORM schema.
        Column("id", String(36), primary_key=True),
        Column("observed_spheres", JSON(), nullable=True),
    )


def _apply_migration(connection, function_name: str = "upgrade") -> None:
    migration = _migration_module()
    operations = Operations(MigrationContext.configure(connection))
    original_op = migration.op
    migration.op = operations
    try:
        getattr(migration, function_name)()
    finally:
        migration.op = original_op


def test_mapping_removal_and_deduplication() -> None:
    migration = _migration_module()
    unknown: Counter[str] = Counter()

    assert migration._canonicalize_value(
        ["money", "shopping", "finance", "decisions", "work", "work"],
        unknown,
    ) == ["finance", "work"]
    assert not unknown


def test_unknown_values_abort_with_occurrence_counts() -> None:
    engine = create_engine("sqlite://")
    table = _table()
    table.metadata.create_all(engine)
    with engine.begin() as connection:
        connection.execute(
            insert(table),
            {"id": "unknown-row", "observed_spheres": ["money", "mystery", "mystery"]},
        )
        with pytest.raises(RuntimeError, match=r"mystery=2"):
            _apply_migration(connection)
        row = connection.execute(select(table.c.observed_spheres)).scalar_one()
        assert row == ["money", "mystery", "mystery"]
    engine.dispose()


def test_empty_and_second_upgrade_are_noops() -> None:
    engine = create_engine("sqlite://")
    table = _table()
    table.metadata.create_all(engine)
    with engine.begin() as connection:
        _apply_migration(connection)
        connection.execute(
            insert(table),
            {"id": "canonical-row", "observed_spheres": ["finance", "work"]},
        )
        _apply_migration(connection)
        row = connection.execute(select(table.c.observed_spheres)).scalar_one()
        assert row == ["finance", "work"]
    engine.dispose()
