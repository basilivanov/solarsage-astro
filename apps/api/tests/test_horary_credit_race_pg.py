# ############################################################################
# AI_HEADER: MODULE_TEST_HORARY_CREDIT_RACE_PG
# ROLE: Real PostgreSQL integration concurrency test for weekly-free credit creation.
# DEPENDENCIES: pytest, sqlalchemy, app.services.horary_credit_service
# GRACE_ANCHORS: [CONCURRENCY_TEST]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORARY-CREDIT-RACE-PG
# purpose: Test concurrent get_or_create_current_weekly_free calls against real PostgreSQL instance.
# owns:
#   - apps/api/tests/test_horary_credit_race_pg.py
# inputs: real postgres database (astro_test)
# outputs: test assertions
# dependencies: app.services.horary_credit_service, app.db.models
# side_effects: creates and drops astro_test postgres database
# emitted_logs: none
# failure_policy: fails test if race condition produces 500 or duplicate rows
# END_MODULE_CONTRACT: M-TEST-HORARY-CREDIT-RACE-PG

# START_MODULE_MAP: M-TEST-HORARY-CREDIT-RACE-PG
# public_entrypoints:
#   - test_weekly_free_concurrency_race_pg
# semantic_blocks:
#   - CONCURRENCY_TEST: real postgres weekly-free insert race test
# owned_tests:
#   - apps/api/tests/test_horary_credit_race_pg.py
# END_MODULE_MAP: M-TEST-HORARY-CREDIT-RACE-PG

import asyncio
import os
import subprocess
import uuid
from datetime import date, datetime, timedelta, timezone
import pytest
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

from app.db.models import User, UserProfile, AccessLedger, HoraryCredit
from app.services.horary_credit_service import HoraryCreditService

PG_URL = "postgresql+asyncpg://astro:astro_dev_password@localhost:5433/astro_test"


@pytest.fixture(scope="module")
def setup_pg_database():
    """Create disposable astro_test postgres database and apply alembic migrations."""
    subprocess.run(
        ["docker", "exec", "solarsage-db", "psql", "-U", "astro", "-d", "postgres", "-c", "DROP DATABASE IF EXISTS astro_test;"],
        check=True,
    )
    subprocess.run(
        ["docker", "exec", "solarsage-db", "psql", "-U", "astro", "-d", "postgres", "-c", "CREATE DATABASE astro_test;"],
        check=True,
    )

    env = os.environ.copy()
    env["DATABASE_URL"] = PG_URL
    api_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    subprocess.run(
        ["alembic", "upgrade", "head"],
        cwd=api_dir,
        env=env,
        check=True,
        capture_output=True,
    )

    yield PG_URL

    subprocess.run(
        ["docker", "exec", "solarsage-db", "psql", "-U", "astro", "-d", "postgres", "-c", "DROP DATABASE IF EXISTS astro_test;"],
        check=False,
    )


# START_BLOCK: CONCURRENCY_TEST
@pytest.mark.integration
@pytest.mark.asyncio
async def test_weekly_free_concurrency_race_pg(setup_pg_database):
    """Test two concurrent get_or_create_current_weekly_free callers receive the same row on Postgres."""
    engine = create_async_engine(PG_URL, echo=False)
    async_session_factory = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    user_id = uuid.uuid4()
    now = datetime.now(timezone.utc)
    today = now.date()

    async with async_session_factory() as session:
        user = User(id=user_id, tg_user_id=999888777)
        session.add(user)
        profile = UserProfile(user_id=user_id, first_name="Test", is_onboarded=True)
        session.add(profile)
        ledger = AccessLedger(
            id=uuid.uuid4(),
            user_id=user_id,
            entry_type="subscription",
            days_granted=22,
            start_date=today - timedelta(days=2),
            end_date=today + timedelta(days=20),
        )
        session.add(ledger)
        await session.commit()

    async def caller_task():
        async with async_session_factory() as s:
            svc = HoraryCreditService(s)
            c = await svc.get_or_create_current_weekly_free(user_id, now)
            await s.commit()
            return c.id if c else None

    c1_id, c2_id = await asyncio.gather(caller_task(), caller_task())

    assert c1_id is not None, "Caller 1 should receive a credit"
    assert c2_id is not None, "Caller 2 should receive a credit"
    assert c1_id == c2_id, f"Both callers must return the exact same canonical row ID! ({c1_id} vs {c2_id})"

    async with async_session_factory() as s:
        res = await s.execute(
            select(func.count(HoraryCredit.id)).where(
                HoraryCredit.user_id == user_id,
                HoraryCredit.source == "subscription_weekly_free",
            )
        )
        count = res.scalar()
        assert count == 1, f"Database must contain exactly 1 weekly_free row, found {count}"

    await engine.dispose()
# END_BLOCK: CONCURRENCY_TEST
