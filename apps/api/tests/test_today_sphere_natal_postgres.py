# ############################################################################
# AI_HEADER: TEST_TODAY-SPHERE-NATAL-POSTGRES — PostgreSQL migration/cache proof.
# ROLE: Rehearses migration 0030 and proves the unique profile/sphere/prompt
#   identity has one concurrent insert winner in an isolated temporary schema.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-NATAL-POSTGRES
# purpose: Validate the real PostgreSQL table shape, reversible migration, and
#   concurrent unique identity behavior for static sphere natal content.
# owns:
#   - apps/api/tests/test_today_sphere_natal_postgres.py
# inputs: TODAY_TEST_POSTGRES_URL and temporary schema names.
# outputs: migration upgrade/downgrade and one-winner concurrency evidence.
# dependencies: SQLAlchemy async PostgreSQL, Alembic Operations, User and
#   TodaySphereNatalNarrative models.
# side_effects: creates/drops one temporary schema; never touches application tables.
# emitted_logs: none.
# invariants: missing/non-PostgreSQL URL fails explicitly; no SQLite substitutes
#   this acceptance test.
# failure_policy: pytest fails closed on absent URL, migration drift, or duplicate winners.
# END_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-NATAL-POSTGRES

# START_MODULE_MAP: M-TEST-TODAY-SPHERE-NATAL-POSTGRES
# public_entrypoints:
#   - test_migration_upgrade_and_downgrade_round_trip
#   - test_concurrent_same_identity_has_one_winner
# semantic_blocks:
#   - MIGRATION_ROUND_TRIP: isolated 0030 upgrade/downgrade rehearsal.
#   - CONCURRENT_UNIQUE: independent transactions competing for one identity.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SPHERE-NATAL-POSTGRES

from __future__ import annotations

import asyncio
import importlib.util
import os
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, inspect, insert, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.db.models import TodaySphereNatalNarrative, User


POSTGRES_URL = os.getenv("TODAY_TEST_POSTGRES_URL")
ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.integration


def _migration_module():
    path = ROOT / "apps/api/alembic/versions/0030_today_sphere_natal_narratives.py"
    spec = importlib.util.spec_from_file_location("today_sphere_natal_migration", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("0030 migration module unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run_migration(sync_connection, function_name: str) -> None:
    migration = _migration_module()
    operations = Operations(MigrationContext.configure(sync_connection))
    original_op = migration.op
    migration.op = operations
    try:
        getattr(migration, function_name)()
    finally:
        migration.op = original_op


async def _set_schema(db: AsyncSession, schema: str) -> None:
    await db.execute(text(f'SET search_path TO "{schema}"'))


@pytest.fixture(scope="module")
async def postgres_context():
    if not POSTGRES_URL:
        pytest.fail("TODAY_TEST_POSTGRES_URL is required for real PostgreSQL acceptance")
    engine = create_async_engine(POSTGRES_URL, poolclass=NullPool)
    schema = f"today_sphere_natal_test_{uuid4().hex}"
    async with engine.begin() as conn:
        if conn.dialect.name != "postgresql":
            pytest.fail(
                "TODAY_TEST_POSTGRES_URL must point to PostgreSQL, "
                f"got dialect '{conn.dialect.name}'"
            )
        await conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        await conn.run_sync(User.__table__.create)
        await conn.run_sync(lambda sync_connection: _run_migration(sync_connection, "upgrade"))

    yield engine, schema

    async with engine.begin() as conn:
        await conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
    await engine.dispose()


@pytest.fixture
def session_factory(postgres_context):
    engine, _schema = postgres_context
    return async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


@pytest.mark.asyncio
async def test_migration_upgrade_and_downgrade_round_trip(postgres_context) -> None:
    engine, schema = postgres_context
    async with engine.begin() as conn:
        await conn.execute(text(f'SET search_path TO "{schema}"'))
        tables = await conn.run_sync(lambda sync_connection: inspect(sync_connection).get_table_names())
        assert "today_sphere_natal_narratives" in tables
        await conn.run_sync(lambda sync_connection: _run_migration(sync_connection, "downgrade"))
        tables_after_downgrade = await conn.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
        assert "today_sphere_natal_narratives" not in tables_after_downgrade
        await conn.run_sync(lambda sync_connection: _run_migration(sync_connection, "upgrade"))
        tables_after_upgrade = await conn.run_sync(
            lambda sync_connection: inspect(sync_connection).get_table_names()
        )
        assert "today_sphere_natal_narratives" in tables_after_upgrade


async def _create_user(session_factory, schema: str) -> UUID:
    async with session_factory() as db:
        await _set_schema(db, schema)
        user = User(tg_user_id=uuid4().int % 2_000_000_000)
        db.add(user)
        await db.commit()
        return user.id


async def _insert_same_identity(session_factory, schema: str, user_id: UUID, marker: str) -> str:
    async with session_factory() as db:
        await _set_schema(db, schema)
        try:
            await db.execute(
                insert(TodaySphereNatalNarrative).values(
                    id=uuid4(),
                    user_id=user_id,
                    profile_hash="p" * 64,
                    sphere_key="work",
                    prompt_version="sphere-natal-v1",
                    content_json={
                        "paragraphs": [
                            {
                                "text": f"Победитель {marker}",
                                "sourceFactIds": ["natal:planet:SUN"],
                            }
                        ]
                    },
                )
            )
            await db.commit()
            return "won"
        except IntegrityError:
            await db.rollback()
            return "lost"


@pytest.mark.asyncio
async def test_concurrent_same_identity_has_one_winner(postgres_context, session_factory) -> None:
    _engine, schema = postgres_context
    user_id = await _create_user(session_factory, schema)
    outcomes = await asyncio.gather(
        _insert_same_identity(session_factory, schema, user_id, "a"),
        _insert_same_identity(session_factory, schema, user_id, "b"),
    )
    assert sorted(outcomes) == ["lost", "won"]

    async with session_factory() as db:
        await _set_schema(db, schema)
        count = await db.scalar(
            select(func.count()).select_from(TodaySphereNatalNarrative).where(
                TodaySphereNatalNarrative.user_id == user_id
            )
        )
        assert count == 1
