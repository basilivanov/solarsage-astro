# ############################################################################
# AI_HEADER: MODULE_PROFILE_SERVICE
# ROLE: Read/write user_profiles + user upsert + invalidation marker.
# DEPENDENCIES: sqlalchemy.ext.asyncio, app.db.models, app.schemas.profile
# GRACE_ANCHORS: [USER_UPSERT, PROFILE_READ, PROFILE_WRITE, INVALIDATION_MARKER]
# ############################################################################

# START_MODULE_CONTRACT: M-PROFILE.service
# purpose: Service-layer helpers for the auth+profile routes:
#   - get_or_create_user() upserts a User by tg_user_id (stable across logins)
#   - read_profile() returns (and lazily creates) the user_profiles row
#   - update_profile() applies a partial ProfileWrite + marks dirty
# owns:
#   - apps/api/app/services/profile_service.py
# inputs:
#   - AsyncSession, TelegramUser, ProfileWrite
# outputs:
#   - User, UserProfile, mark_profile_dirty(user_id)
# invariants:
#   - get_or_create_user is idempotent: same tg_user_id never produces two rows
#   - read_profile is idempotent: ensures one row per user
#   - update_profile applies partial semantics (model_dump(exclude_unset=True))
# failure_policy:
#   - any DB error propagates; the routes do not catch them
# non_goals:
#   - no caching (Redis lands in W-CACHE)
#   - no audit log (W-1.6 logging spine retrofit)
# END_MODULE_CONTRACT: M-PROFILE.service

# START_MODULE_MAP: M-PROFILE.service
# public_entrypoints:
#   - get_or_create_user
#   - read_profile
#   - update_profile
#   - mark_profile_dirty
# semantic_blocks:
#   - USER_UPSERT: get_or_create_user by tg_user_id
#   - PROFILE_READ: read_profile (lazy create)
#   - PROFILE_WRITE: update_profile (partial)
#   - INVALIDATION_MARKER: mark_profile_dirty stub (UC-PROFILE-EDIT)
# owned_tests:
#   - apps/api/tests/test_profile_endpoints.py
# END_MODULE_MAP: M-PROFILE.service

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile
from app.schemas.profile import ProfileWrite
from app.services.telegram_auth import TelegramUser


# START_BLOCK: USER_UPSERT
async def get_or_create_user(
    db: AsyncSession, tg: TelegramUser
) -> tuple[User, bool]:
    """Insert or update a User row keyed by tg_user_id. Returns (user, is_new)."""
    existing = (
        await db.execute(select(User).where(User.tg_user_id == tg.id))
    ).scalar_one_or_none()
    if existing is None:
        user = User(
            id=uuid.uuid4(),
            tg_user_id=tg.id,
            tg_username=tg.username,
        )
        db.add(user)
        await db.flush()
        return user, True
    existing.tg_username = tg.username
    await db.flush()
    return existing, False
# END_BLOCK: USER_UPSERT


# START_BLOCK: PROFILE_READ
async def read_profile(db: AsyncSession, user_id: uuid.UUID) -> UserProfile:
    """Return the user_profiles row, creating an empty one if absent."""
    row = (
        await db.execute(
            select(UserProfile).where(UserProfile.user_id == user_id)
        )
    ).scalar_one_or_none()
    if row is None:
        row = UserProfile(user_id=user_id)
        db.add(row)
        await db.flush()
    return row
# END_BLOCK: PROFILE_READ


# START_BLOCK: PROFILE_WRITE
async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, payload: ProfileWrite
) -> UserProfile:
    """Apply a partial profile update + mark the user as cache-dirty."""
    profile = await read_profile(db, user_id)

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    if "first_name" in data:
        profile.first_name = data["first_name"]
    birth = data.get("birth")
    if isinstance(birth, dict):
        for f in (
            "birthday",
            "birth_time",
            "birth_city",
            "birth_lat",
            "birth_lon",
            "birth_tz",
        ):
            if f in birth:
                setattr(profile, f, birth[f])

    # W-2.7: Mark user as onboarded if they have birthday and birth_city
    # This allows completing onboarding flow
    if profile.birthday and profile.birth_city and not profile.is_onboarded:
        profile.is_onboarded = True

    await db.flush()
    mark_profile_dirty(user_id)
    return profile
# END_BLOCK: PROFILE_WRITE


# START_BLOCK: INVALIDATION_MARKER
def mark_profile_dirty(user_id: uuid.UUID) -> None:
    """UC-PROFILE-EDIT invalidation hook (W-1.2 stub).

    When the cache layer lands (W-CACHE), this function will evict per-user
    cached payloads. For now it is intentionally a no-op so that callers
    can wire the call site once and never have to be revisited.
    """
    # TODO(W-CACHE): evict cached day/calendar payloads for user_id.
    # TODO(W-1.6): log.event("profile.invalidate_caches.requested", {user_id_hash})
    return None
# END_BLOCK: INVALIDATION_MARKER
