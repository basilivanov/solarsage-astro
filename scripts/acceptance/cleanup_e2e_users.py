#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: ACCEPTANCE_CLEANUP_E2E_USERS — ephemeral e2e user cleanup
# ROLE: Deletes run-salted test users created by Playwright fixtures from the
#       ephemeral acceptance database; verifies deleted counts; never prod.
# DEPENDENCIES: apps/api app.db models, SQLAlchemy async, DATABASE_URL env
# ############################################################################

# START_MODULE_CONTRACT: M-ACCEPTANCE-CLEANUP-E2E-USERS
# purpose: External cleanup adapter for the real-E2E integrity slice. Reads
#   the run's created-users JSONL file (E2E_CREATED_USERS_FILE) and deletes
#   exactly those users from the ephemeral acceptance DB, printing per-id and
#   total deleted counts. Guarded fail-closed: requires APP_ENV=test or
#   acceptance AND a localhost DATABASE_URL; refuses anything else.
# owns:
#   - scripts/acceptance/cleanup_e2e_users.py
# inputs: E2E_CREATED_USERS_FILE (default /tmp/solarsage-e2e-created-users.jsonl),
#   APP_ENV (must be test|acceptance), DATABASE_URL (localhost only).
# outputs: stdout per-id + total deleted counts; exit 0 on success.
# dependencies: app.db.models (User), app.db.session.
# side_effects: DELETE of the listed users (cascade to profiles/sessions)
#   in the ephemeral acceptance DB only.
# emitted_logs: none.
# invariants:
#   - no production target ever; non-local DB or wrong APP_ENV => hard fail.
# failure_policy: exit non-zero on guard/DB errors.
# END_MODULE_CONTRACT: M-ACCEPTANCE-CLEANUP-E2E-USERS

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path


def fail(message: str) -> None:
    sys.stderr.write(f"Error: {message}\n")
    sys.exit(1)


async def main() -> int:
    app_env = os.environ.get("APP_ENV", "")
    if app_env not in ("test", "acceptance"):
        fail(f"APP_ENV must be test or acceptance for cleanup (got {app_env!r})")
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        fail("DATABASE_URL is required")
    from urllib.parse import urlparse
    try:
        parsed = urlparse(db_url.replace("postgresql+asyncpg://", "postgresql://"))
        hostname = parsed.hostname
    except ValueError as exc:
        fail(f"DATABASE_URL is not parseable: {exc}")
    if hostname not in ("localhost", "127.0.0.1", "::1"):
        fail(f"refusing cleanup against non-local database host {hostname!r} (ephemeral acceptance DB only)")

    users_file = Path(os.environ.get("E2E_CREATED_USERS_FILE", "/tmp/solarsage-e2e-created-users.jsonl"))
    if not users_file.is_file():
        print(f"no created-users file at {users_file} — nothing to clean")
        return 0
    tg_ids: set[int] = set()
    for line in users_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            tg_ids.add(int(json.loads(line)["tg_user_id"]))
        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            fail(f"malformed created-users line {line!r}: {exc}")

    if not tg_ids:
        print("no created users recorded — nothing to clean")
        return 0

    from sqlalchemy import delete, func, select
    from app.db.models import User
    from app.db.session import SessionLocal

    async with SessionLocal() as db:
        total = 0
        for tg_id in sorted(tg_ids):
            existing = (await db.execute(select(User.id).where(User.tg_user_id == tg_id))).scalar_one_or_none()
            if existing is None:
                print(f"tg_user_id={tg_id}: absent (already clean)")
                continue
            await db.execute(delete(User).where(User.tg_user_id == tg_id))
            remaining = (await db.execute(select(func.count()).select_from(User).where(User.tg_user_id == tg_id))).scalar_one()
            if remaining != 0:
                fail(f"cleanup verification failed for tg_user_id={tg_id}: {remaining} rows left")
            total += 1
            print(f"tg_user_id={tg_id}: deleted 1 (verified 0 left)")
        await db.commit()
        print(f"cleanup OK: {total} user(s) deleted of {len(tg_ids)} recorded")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
