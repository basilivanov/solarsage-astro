# ############################################################################
# AI_HEADER: MODULE_DB_SESSION
# ROLE: Async SQLAlchemy engine, session factory, and declarative Base.
# DEPENDENCIES: sqlalchemy[asyncio], app.core.config
# GRACE_ANCHORS: [DECLARATIVE_BASE, ENGINE_CONSTRUCTION, SESSION_FACTORY, SESSION_LIFECYCLE]
# ############################################################################

# START_MODULE_CONTRACT: M-DB-SESSION
# purpose: Own the async SQLAlchemy engine, session factory, and declarative
#   Base used by every feature module that touches the database.
# owns:
#   - apps/api/app/db/session.py
#   - apps/api/app/db/__init__.py
# inputs:
#   - settings.database_url (from M-CONFIG)
# outputs:
#   - Base (DeclarativeBase) for ORM models registered in later waves
#   - engine (AsyncEngine) for low-level access and Alembic
#   - SessionLocal (async_sessionmaker[AsyncSession]) for request-scoped sessions
#   - get_session() FastAPI dependency yielding AsyncSession
# dependencies:
#   - M-CONFIG (reads database_url)
#   - SQLAlchemy 2.x async stack
# side_effects:
#   - opens a TCP/file connection to the configured database when engine is used
# invariants:
#   - exactly one engine instance per process
#   - Base.metadata is the single source of truth for Alembic autogenerate
#   - get_session always closes the session, even on exception
# failure_policy:
#   - connection errors propagate to the caller; FastAPI surfaces 500
#   - this module never swallows DB errors silently
# non_goals:
#   - no model definitions (deferred to W-1.2)
#   - no migration logic (lives in alembic/)
#   - no business logic
# END_MODULE_CONTRACT: M-DB-SESSION

# START_MODULE_MAP: M-DB-SESSION
# public_entrypoints:
#   - Base
#   - engine
#   - SessionLocal
#   - get_session
# semantic_blocks:
#   - DECLARATIVE_BASE: Base(DeclarativeBase) for ORM models
#   - ENGINE_CONSTRUCTION: create_async_engine(settings.database_url)
#   - SESSION_FACTORY: async_sessionmaker bound to engine
#   - SESSION_LIFECYCLE: get_session() dependency, async-with cleanup
# owned_tests:
#   - apps/api/tests/test_health.py (smoke; deeper DB tests arrive with W-1.2)
# END_MODULE_MAP: M-DB-SESSION

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.core.config import settings


# START_BLOCK: DECLARATIVE_BASE
class Base(DeclarativeBase):
    """Project-wide declarative base for ORM models."""
# END_BLOCK: DECLARATIVE_BASE


# START_BLOCK: ENGINE_CONSTRUCTION
engine = create_async_engine(settings.database_url, future=True)
# END_BLOCK: ENGINE_CONSTRUCTION

# START_BLOCK: SESSION_FACTORY
SessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)
# END_BLOCK: SESSION_FACTORY


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    # START_FUNCTION_CONTRACT: M-DB-SESSION.get_session
    # purpose: Provide each request with its own AsyncSession bound to the
    #   shared engine, and guarantee cleanup.
    # inputs: none (consumed via FastAPI Depends)
    # returns: async generator yielding exactly one AsyncSession
    # side_effects: opens and closes a DB session
    # emitted_logs: none in W-1.1 (logging arrives with M-LOGS)
    # error_behavior: propagates exceptions; the async-with block ensures
    #   the underlying connection is returned to the pool in all paths
    # END_FUNCTION_CONTRACT: M-DB-SESSION.get_session

    # START_BLOCK: SESSION_LIFECYCLE
    async with SessionLocal() as session:
        yield session
    # END_BLOCK: SESSION_LIFECYCLE
