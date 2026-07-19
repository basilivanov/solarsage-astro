#!/usr/bin/env python3
# ############################################################################
# AI_HEADER: ACCEPTANCE_SEED_AUDIT_PROFILE — ephemeral audit seed adapter
# ROLE: Seeds the EXACT committed audit fixture profile into the EPHEMERAL
#       acceptance DB so make audit-day-freeze can run; never production.
# DEPENDENCIES: apps/api app.db models, SQLAlchemy async, DATABASE_URL env
# ############################################################################

# START_MODULE_CONTRACT: M-ACCEPTANCE-SEED-AUDIT-PROFILE
# purpose: External seeded-fixture adapter (the ONLY addition for the audit
#   freeze gate; audit_today.py itself is untouched). Reads the committed
#   fixture artifacts/audit/2026-07-08/00_input_profile.json and seeds
#   exactly that user+profile (uuid, tg id, birth, current, onboarded) into
#   the ephemeral acceptance database. Fail-closed when the fixture is
#   missing or malformed — no arbitrary profiles are ever seeded.
# owns:
#   - scripts/acceptance/seed_audit_profile.py
# inputs: DATABASE_URL env; optional --fixture path.
# outputs: stdout line "uuid=<uuid>"; exit 0 on success.
# dependencies: app.db.models (User, UserProfile), app.db.session.
# side_effects: DELETE+INSERT of the seed user in the target DB (ephemeral
#   acceptance DB only; a guard refuses non-local database hosts).
# emitted_logs: none.
# invariants:
#   - seeds EXACTLY the committed fixture; no invented values.
#   - refuses non-localhost database hosts.
# failure_policy: exit non-zero on guard/fixture/DB errors.
# END_MODULE_CONTRACT: M-ACCEPTANCE-SEED-AUDIT-PROFILE

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import uuid
from datetime import date, time
from pathlib import Path

DEFAULT_FIXTURE = "artifacts/audit/2026-07-08/00_input_profile.json"


def load_fixture(path: Path) -> dict:
    if not path.is_file():
        sys.exit(f"Error: committed audit fixture is missing: {path}")
    data = json.loads(path.read_text(encoding="utf-8"))
    required = ("user_id", "tg_user_id", "is_onboarded", "gender", "birth", "current")
    missing = [k for k in required if k not in data]
    if missing:
        sys.exit(f"Error: fixture missing keys {missing}: {path}")
    return data


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fixture", default=DEFAULT_FIXTURE)
    args = parser.parse_args()

    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        sys.exit("Error: DATABASE_URL is required")
    for marker in ("127.0.0.1", "localhost", "postgres:"):
        if marker in db_url:
            break
    else:
        sys.exit("Error: refusing to seed a non-local database (ephemeral acceptance DB only)")

    fixture = load_fixture(Path(args.fixture))
    os.environ.setdefault("APP_ENV", "development")
    from sqlalchemy import delete, select
    from app.db.models import User, UserProfile
    from app.db.session import SessionLocal

    tg_user_id = int(fixture["tg_user_id"])
    birth = fixture["birth"]
    current = fixture["current"]
    by, bm, bd = (int(part) for part in birth["date"].split("-"))
    th, tm = (int(part) for part in birth["time"].split(":"))

    async with SessionLocal() as db:
        existing = (await db.execute(select(User).where(User.tg_user_id == tg_user_id))).scalar_one_or_none()
        if existing is not None:
            await db.execute(delete(User).where(User.id == existing.id))
            await db.flush()

        user = User(
            id=uuid.UUID(fixture["user_id"]),
            tg_user_id=tg_user_id,
            tg_username=fixture.get("tg_username"),
        )
        db.add(user)
        await db.flush()
        profile = UserProfile(
            user_id=user.id,
            gender=fixture["gender"],
            birthday=date(by, bm, bd),
            birth_time=time(th, tm),
            birth_city=birth["city"],
            birth_lat=birth["lat"],
            birth_lon=birth["lon"],
            birth_tz=birth["tz"],
            current_city=current["city"],
            current_lat=current["lat"],
            current_lon=current["lon"],
            current_tz=current["tz"],
            is_onboarded=bool(fixture["is_onboarded"]),
        )
        db.add(profile)
        await db.commit()
        print(f"uuid={user.id}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
