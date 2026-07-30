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
#   - missing_onboarding_fields() checks base onboarding completeness
# owns:
#   - apps/api/app/services/profile_service.py
# inputs:
#   - AsyncSession, TelegramUser, ProfileWrite
# outputs:
#   - User, UserProfile, missing_onboarding_fields, mark_profile_dirty(user_id)
#   - InvalidBirthTimeState for stable profile-wire validation failures
# invariants:
#   - get_or_create_user is idempotent: same tg_user_id never produces two rows
#   - read_profile is idempotent: ensures one row per user
#   - update_profile applies partial semantics (model_dump(exclude_unset=True))
#   - missing_onboarding_fields evaluates birthday, non-empty birth_city, and gender in {male, female}
#   - birth-time validation runs against merged state before any profile field mutation
#   - only safe field names and reason enums are emitted in profile logs
# emitted_logs:
#   - profile.lazy_created, profile.updated, profile.update_failed
# failure_policy:
#   - any DB error propagates; the routes do not catch them
# non_goals:
#   - no caching (Redis lands in W-CACHE)
#   - no audit log beyond the canonical profile event registry
# END_MODULE_CONTRACT: M-PROFILE.service

# START_MODULE_MAP: M-PROFILE.service
# public_entrypoints:
#   - get_or_create_user
#   - read_profile
#   - update_profile
#   - InvalidBirthTimeState
#   - missing_onboarding_fields
#   - mark_profile_dirty
# semantic_blocks:
#   - USER_UPSERT: get_or_create_user by tg_user_id
#   - PROFILE_READ: read_profile (lazy create)
#   - PROFILE_WRITE: update_profile (partial)
#   - BIRTH_TIME_STATE: merged exact/bucket/unknown validation
#   - BASE_ONBOARDING_CHECK: missing_onboarding_fields helper
#   - INVALIDATION_MARKER: mark_profile_dirty stub (UC-PROFILE-EDIT)
# owned_tests:
#   - apps/api/tests/test_profile_endpoints.py
#   - apps/api/tests/test_profile_readiness.py
# END_MODULE_MAP: M-PROFILE.service

from __future__ import annotations

import uuid
from decimal import Decimal as D

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_block, log_event
from app.db.models import User, UserProfile
from app.schemas.profile import LocationData, ProfileWrite
from app.services.telegram_auth import TelegramUser


# START_BLOCK: BASE_ONBOARDING_CHECK
def missing_onboarding_fields(profile: UserProfile | None) -> list[str]:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service.missing_onboarding_fields
    # purpose: Return deterministic list of missing base onboarding fields.
    # inputs: profile (UserProfile | None)
    # returns: list[str] containing missing fields in order ["birthday", "birth_city", "gender"]
    # side_effects: none (pure function)
    # emitted_logs: none
    # error_behavior: returns full missing list if profile is None
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service.missing_onboarding_fields
    """Return deterministic list of missing base onboarding fields."""
    if profile is None:
        return ["birthday", "birth_city", "gender"]

    missing: list[str] = []

    if profile.birthday is None:
        missing.append("birthday")

    if not profile.birth_city:
        missing.append("birth_city")

    if profile.gender not in ("male", "female"):
        missing.append("gender")

    return missing
# END_BLOCK: BASE_ONBOARDING_CHECK


# START_BLOCK: LOCATION_APPLY
def _apply_location(
    profile: UserProfile, loc: dict | LocationData | None, prefix: str
) -> None:
    if loc is None:
        return
    if isinstance(loc, dict):
        loc = LocationData(**loc)
    setattr(profile, f"{prefix}_city", loc.city)
    setattr(
        profile,
        f"{prefix}_lat",
        D(str(loc.lat)) if loc.lat is not None else None,
    )
    setattr(
        profile,
        f"{prefix}_lon",
        D(str(loc.lon)) if loc.lon is not None else None,
    )
    setattr(profile, f"{prefix}_tz", loc.tz)
# END_BLOCK: LOCATION_APPLY


# START_BLOCK: USER_UPSERT
async def get_or_create_user(
    db: AsyncSession, tg: TelegramUser
) -> tuple[User, bool]:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service.get_or_create_user
    # purpose: Upsert a User row by tg_user_id.
    # inputs: db (AsyncSession), tg (TelegramUser)
    # returns: tuple[User, bool] — (user, is_new)
    # side_effects: creates or updates User row
    # emitted_logs: none
    # error_behavior: DB errors propagate
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service.get_or_create_user
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
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service.read_profile
    # purpose: Return user_profiles row, lazy-create if absent.
    # inputs: db (AsyncSession), user_id (UUID)
    # returns: UserProfile with all profile fields
    # side_effects: creates empty UserProfile row if not exists
    # emitted_logs: profile.lazy_created
    # error_behavior: DB errors propagate
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service.read_profile
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
        with log_block(
            slice="W-PROFILE", module="M-PROFILE-SERVICE", block="PROFILE_READ"
        ):
            log_event(
                "profile.lazy_created",
                payload={"reason": "missing_profile"},
            )
    return row
# END_BLOCK: PROFILE_READ


# START_BLOCK: BIRTH_TIME_STATE
class InvalidBirthTimeState(ValueError):
    """Stable, safe reason wrapper for merged profile birth-time failures."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(reason)


def _merged_birth_time_state(
    profile: UserProfile, birth: dict | None
) -> tuple[object, object, object, object]:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service._merged_birth_time_state
    # purpose: Build the candidate birth-time state without mutating profile.
    # inputs: profile — persisted state; birth — partial nested write fields.
    # returns: (time, mode, bucket, dismissed) merged candidate values.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: none; shape validation is delegated to the next helper.
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service._merged_birth_time_state
    values = {
        "birth_time": profile.birth_time,
        "birth_time_mode": profile.birth_time_mode,
        "birth_time_bucket": profile.birth_time_bucket,
        "birth_time_prompt_dismissed": profile.birth_time_prompt_dismissed,
    }
    if isinstance(birth, dict):
        for field in values:
            if field in birth:
                values[field] = birth[field]
    return (
        values["birth_time"],
        values["birth_time_mode"],
        values["birth_time_bucket"],
        values["birth_time_prompt_dismissed"],
    )


def _validate_birth_time_state(
    *,
    birth_time: object,
    birth_time_mode: object,
    birth_time_bucket: object,
    birth_time_prompt_dismissed: object,
    previous_prompt_dismissed: bool,
) -> None:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service._validate_birth_time_state
    # purpose: Enforce atomic exact/bucket/unknown and dismissal transition rules.
    # inputs: Merged birth-time values plus persisted dismissal flag.
    # returns: None for an accepted state.
    # side_effects: none.
    # emitted_logs: none; caller emits profile.update_failed with reason enum.
    # error_behavior: Raises InvalidBirthTimeState with a safe reason enum.
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service._validate_birth_time_state
    if birth_time_mode not in {"exact", "bucket", "unknown"}:
        raise InvalidBirthTimeState("mode_required")
    if birth_time_prompt_dismissed not in {True, False}:
        raise InvalidBirthTimeState("dismissed_must_be_boolean")
    if previous_prompt_dismissed and birth_time_prompt_dismissed is False:
        raise InvalidBirthTimeState("dismissal_irreversible")

    if birth_time_mode == "exact":
        if birth_time is None:
            raise InvalidBirthTimeState("exact_requires_time")
        if birth_time_bucket is not None:
            raise InvalidBirthTimeState("exact_forbids_bucket")
        return

    if birth_time_mode == "bucket":
        if birth_time is not None:
            raise InvalidBirthTimeState("bucket_forbids_time")
        if birth_time_bucket not in {"night", "morning", "day", "evening"}:
            raise InvalidBirthTimeState("bucket_requires_valid_bucket")
        return

    if birth_time is not None:
        raise InvalidBirthTimeState("unknown_forbids_time")
    if birth_time_bucket is not None:
        raise InvalidBirthTimeState("unknown_forbids_bucket")


def _profile_changed_fields(data: dict) -> list[str]:
    """Return only safe, stable field names for profile event payloads."""
    fields: list[str] = []
    for field in (
        "first_name",
        "gender",
        "current_location",
        "birthday_location",
    ):
        if field in data:
            fields.append(field)
    birth = data.get("birth")
    if isinstance(birth, dict):
        for field in (
            "birthday",
            "birth_time",
            "birth_time_mode",
            "birth_time_bucket",
            "birth_time_prompt_dismissed",
            "birth_city",
            "birth_lat",
            "birth_lon",
            "birth_tz",
        ):
            if field in birth:
                fields.append(f"birth.{field}")
    return fields
# END_BLOCK: BIRTH_TIME_STATE


# START_BLOCK: PROFILE_WRITE
async def update_profile(
    db: AsyncSession, user_id: uuid.UUID, payload: ProfileWrite
) -> UserProfile:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service.update_profile
    # purpose: Validate merged birth-time state, then apply partial profile
    #   update and mark cache as dirty.
    # inputs: db (AsyncSession), user_id (UUID), payload (ProfileWrite)
    # returns: updated UserProfile
    # side_effects: validates and updates profile row, sets is_onboarded if
    #   conditions met, emits safe profile events, marks cache dirty
    # emitted_logs: profile.updated, profile.update_failed
    # error_behavior: DB errors propagate
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service.update_profile
    """Apply a partial profile update + mark the user as cache-dirty."""
    profile = await read_profile(db, user_id)

    data = payload.model_dump(exclude_unset=True, by_alias=False)
    birth = data.get("birth")
    try:
        merged_time, merged_mode, merged_bucket, merged_dismissed = _merged_birth_time_state(
            profile, birth
        )
        _validate_birth_time_state(
            birth_time=merged_time,
            birth_time_mode=merged_mode,
            birth_time_bucket=merged_bucket,
            birth_time_prompt_dismissed=merged_dismissed,
            previous_prompt_dismissed=profile.birth_time_prompt_dismissed,
        )
    except InvalidBirthTimeState as exc:
        with log_block(
            slice="W-PROFILE", module="M-PROFILE-SERVICE", block="PROFILE_WRITE"
        ):
            log_event(
                "profile.update_failed",
                level="warning",
                payload={"reason": exc.reason},
            )
        raise

    if "first_name" in data:
        profile.first_name = data["first_name"]
    if "gender" in data:
        profile.gender = data["gender"]
    if isinstance(birth, dict):
        for f in (
            "birthday",
            "birth_time",
            "birth_time_mode",
            "birth_time_bucket",
            "birth_time_prompt_dismissed",
            "birth_city",
            "birth_lat",
            "birth_lon",
            "birth_tz",
        ):
            if f in birth:
                setattr(profile, f, birth[f])

    _apply_location(profile, data.get("current_location"), "current")
    _apply_location(profile, data.get("birthday_location"), "birthday")

    # W-2.7: Mark user as onboarded if base onboarding fields are complete
    # This allows completing onboarding flow
    if not missing_onboarding_fields(profile) and not profile.is_onboarded:
        profile.is_onboarded = True

    await db.flush()
    with log_block(
        slice="W-PROFILE", module="M-PROFILE-SERVICE", block="PROFILE_WRITE"
    ):
        log_event(
            "profile.updated",
            payload={"changed_fields": _profile_changed_fields(data)},
        )
    mark_profile_dirty(user_id)
    return profile
# END_BLOCK: PROFILE_WRITE


# START_BLOCK: INVALIDATION_MARKER
def mark_profile_dirty(user_id: uuid.UUID) -> None:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.service.mark_profile_dirty
    # purpose: Mark user's cached payloads as dirty (stub).
    # inputs: user_id (UUID)
    # returns: None
    # side_effects: none (stub for W-CACHE)
    # emitted_logs: none (TODO: W-1.6)
    # error_behavior: never raises
    # END_FUNCTION_CONTRACT: F-M-PROFILE.service.mark_profile_dirty
    """UC-PROFILE-EDIT invalidation hook (W-1.2 stub).

    When the cache layer lands (W-CACHE), this function will evict per-user
    cached payloads. For now it is intentionally a no-op so that callers
    can wire the call site once and never have to be revisited.
    """
    # TODO(W-CACHE): evict cached day/calendar payloads for user_id.
    # TODO(W-1.6): log.event("profile.invalidate_caches.requested", {user_id_hash})
    return None
# END_BLOCK: INVALIDATION_MARKER
