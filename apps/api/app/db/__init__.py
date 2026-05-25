# ############################################################################
# AI_HEADER: MODULE_DB_PACKAGE
# ROLE: Public re-export surface of the db package; no logic of its own.
# DEPENDENCIES: app.db.session
# GRACE_ANCHORS: [DB_PUBLIC_REEXPORTS]
# ############################################################################

# START_MODULE_CONTRACT: M-DB-PACKAGE
# purpose: Provide a stable, discoverable import surface for the db package
#   so callers can `from app.db import Base, engine, SessionLocal, get_session`
#   without depending on the internal module layout (session.py, future
#   models.py, etc.).
# owns:
#   - apps/api/app/db/__init__.py
# inputs:
#   - public symbols defined in M-DB-SESSION (Base, engine, SessionLocal,
#     get_session)
# outputs:
#   - re-exported names listed in __all__
# dependencies:
#   - app.db.session (M-DB-SESSION)
# side_effects:
#   - importing this package transitively constructs the engine and
#     session factory defined in M-DB-SESSION
# invariants:
#   - __all__ is the single source of truth for the package's public API
#   - this file contains no logic, only re-exports
# failure_policy:
#   - any import-time failure from M-DB-SESSION propagates unchanged
# non_goals:
#   - no model definitions (deferred to W-1.2)
#   - no session lifecycle code (lives in M-DB-SESSION)
# END_MODULE_CONTRACT: M-DB-PACKAGE

# START_MODULE_MAP: M-DB-PACKAGE
# public_entrypoints:
#   - Base
#   - SessionLocal
#   - engine
#   - get_session
# semantic_blocks:
#   - DB_PUBLIC_REEXPORTS: re-export of M-DB-SESSION public symbols
# owned_tests:
#   - apps/api/tests/test_health.py (indirect, via FastAPI dependency wiring)
# END_MODULE_MAP: M-DB-PACKAGE

# START_BLOCK: DB_PUBLIC_REEXPORTS
from app.db.session import Base, SessionLocal, engine, get_session

__all__ = ["Base", "SessionLocal", "engine", "get_session"]
# END_BLOCK: DB_PUBLIC_REEXPORTS
