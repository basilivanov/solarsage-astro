# ############################################################################
# AI_HEADER: MODULE_API_PROFILE
# ROLE: HTTP surface for /api/profile (GET, PUT). Owns UC-PROFILE-EDIT.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.profile_service
# GRACE_ANCHORS: [ROUTE_PROFILE_GET, ROUTE_PROFILE_PUT]
# ############################################################################

# START_MODULE_CONTRACT: M-PROFILE.api
# purpose: GET /api/profile returns ProfileRead; PUT /api/profile applies a
#   partial update with atomic merged birth-time validation. On any successful
#   PUT the profile_service marks the user cache-dirty and the route invalidates
#   Today caches.
# owns:
#   - apps/api/app/api/profile.py
# inputs:
#   - user_id from current_user_id dep (M-AUTH-TG.dependencies)
#   - DB session (M-DB-SESSION)
#   - request body conforms to ProfileWrite
# outputs:
#   - APIRouter with GET /api/profile, PUT /api/profile
# dependencies:
#   - M-AUTH-TG.dependencies (current_user_id) — sourced from core.dependencies, not from sibling routers
#   - M-PROFILE.service
#   - M-PROMO-CAMPAIGN-SERVICE (PromoCampaignService, PromoDomainError)
# invariants:
#   - GET on a brand-new user lazily creates an empty profile row; never 404.
#   - PUT is partial: omitted fields stay as-is.
#   - birth-time state is explicit and stable on the wire.
#   - invalid merged birth-time state returns 422 with INVALID_BIRTH_TIME_STATE
#     before any profile field mutation.
#   - Response NEVER carries tg_user_id / token_hash / other privacy keys.
#   - On onboarding completion, valid pending_promo_token is auto-applied without disrupting 200 response.
# emitted_logs:
#   - profile.viewed, profile.lazy_created, profile.update_failed
#   - profile.updated, profile.cache_invalidation_requested,
#     profile.cache_invalidated, promo.pending_auto_apply_failed
# failure_policy:
#   - 401 propagates from current_user_id
#   - 422 from FastAPI on invalid body shape or INVALID_BIRTH_TIME_STATE
# non_goals:
#   - no storage of raw profile values in structured event payloads
# END_MODULE_CONTRACT: M-PROFILE.api

# START_MODULE_MAP: M-PROFILE.api
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_PROFILE_GET: GET /api/profile handler
#   - ROUTE_PROFILE_PUT: PUT /api/profile handler
# owned_tests:
#   - apps/api/tests/test_profile_endpoints.py
#   - apps/api/tests/test_promo_pending_auto_apply.py
# END_MODULE_MAP: M-PROFILE.api

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id
from app.core.logging import log_block, log_event
from app.db.models import User, UserProfile
from app.db.session import get_session
from app.schemas.profile import BirthData, LocationData, ProfileRead, ProfileWrite
from app.services.profile_service import (
    InvalidBirthTimeState,
    read_profile,
    update_profile,
)
from app.services.promo_campaign_service import (
    PromoCampaignService,
    PromoDomainError,
)

router = APIRouter()


def _loc_to_data(profile: UserProfile, prefix: str) -> LocationData | None:
    city = getattr(profile, f"{prefix}_city")
    lat = getattr(profile, f"{prefix}_lat")
    lon = getattr(profile, f"{prefix}_lon")
    tz = getattr(profile, f"{prefix}_tz")
    if city is None and lat is None:
        return None
    return LocationData(
        city=city,
        lat=float(lat) if isinstance(lat, Decimal) else lat,
        lon=float(lon) if isinstance(lon, Decimal) else lon,
        tz=tz,
    )


def _to_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        user_id=profile.user_id,
        first_name=profile.first_name,
        gender=profile.gender,
        is_onboarded=profile.is_onboarded,
        birth=BirthData(
            birthday=profile.birthday,
            birth_time=profile.birth_time,
            birth_time_mode=profile.birth_time_mode,
            birth_time_bucket=profile.birth_time_bucket,
            birth_time_prompt_dismissed=profile.birth_time_prompt_dismissed,
            birth_city=profile.birth_city,
            birth_lat=(
                float(profile.birth_lat)
                if isinstance(profile.birth_lat, Decimal)
                else profile.birth_lat
            ),
            birth_lon=(
                float(profile.birth_lon)
                if isinstance(profile.birth_lon, Decimal)
                else profile.birth_lon
            ),
            birth_tz=profile.birth_tz,
        ),
        current_location=_loc_to_data(profile, "current"),
        birthday_location=_loc_to_data(profile, "birthday"),
    )


# START_BLOCK: ROUTE_PROFILE_GET
@router.get("/api/profile", response_model=ProfileRead)
async def get_profile(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> ProfileRead:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.api.get_profile
    # purpose: Get user profile (lazy-creates empty profile if absent).
    # inputs: user_id from session, db session
    # returns: ProfileRead with birth data, locations, onboarding status
    # side_effects: creates empty profile row if not exists
    # emitted_logs: profile.viewed, profile.lazy_created
    # error_behavior: 401 if not authenticated
    # END_FUNCTION_CONTRACT: F-M-PROFILE.api.get_profile
    profile = await read_profile(db, user_id)
    await db.commit()
    with log_block(slice="W-PROFILE", module="M-PROFILE-API", block="ROUTE_PROFILE_GET"):
        log_event("profile.viewed")
    return _to_read(profile)
# END_BLOCK: ROUTE_PROFILE_GET


# START_BLOCK: ROUTE_PROFILE_PUT
@router.put(
    "/api/profile",
    response_model=ProfileRead,
    status_code=status.HTTP_200_OK,
)
async def put_profile(
    body: ProfileWrite,
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> ProfileRead:
    # START_FUNCTION_CONTRACT: F-M-PROFILE.api.put_profile
    # purpose: Apply partial profile update, validate merged birth-time state,
    #   and invalidate cache.
    # inputs: body (ProfileWrite), user_id from session, db session
    # returns: ProfileRead with updated data
    # side_effects: updates profile row, invalidates today cache, auto-applies pending promo token
    # emitted_logs: profile.updated, profile.update_failed,
    #   profile.cache_invalidation_requested, profile.cache_invalidated,
    #   promo.pending_auto_apply_failed
    # error_behavior: 401 if not authenticated, 422 on validation failure
    # END_FUNCTION_CONTRACT: F-M-PROFILE.api.put_profile
    try:
        profile = await update_profile(db, user_id, body)
    except InvalidBirthTimeState as exc:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "INVALID_BIRTH_TIME_STATE", "reason": exc.reason},
        ) from exc

    # W-5.2: Invalidate cache after profile edit
    from app.services.today_service import TodayService

    with log_block(slice="W-PROFILE", module="M-PROFILE-API", block="ROUTE_PROFILE_PUT"):
        log_event(
            "profile.cache_invalidation_requested",
            payload={"reason": "profile_updated"},
        )
    today_service = TodayService(db)
    await today_service.invalidate_cache(user_id)
    with log_block(slice="W-PROFILE", module="M-PROFILE-API", block="ROUTE_PROFILE_PUT"):
        log_event(
            "profile.cache_invalidated",
            payload={"reason": "profile_updated"},
        )

    await db.commit()
    result = _to_read(profile)

    # PROMO-PERSIST-02: Auto-apply pending promo token upon onboarding completion
    user = await db.get(User, user_id)
    if user and user.pending_promo_token and profile.is_onboarded:
        pending_token = user.pending_promo_token
        try:
            promo_service = PromoCampaignService(db)
            await promo_service.redeem(user_id, pending_token)
            user = await db.get(User, user_id)
            if user:
                user.pending_promo_token = None
                await db.commit()
        except PromoDomainError as err:
            if err.code in (
                "INVALID_CODE",
                "CAMPAIGN_EXPIRED",
                "CAMPAIGN_FULL",
                "ALREADY_REDEEMED",
            ):
                user = await db.get(User, user_id)
                if user:
                    user.pending_promo_token = None
                    await db.commit()
            log_event(
                "promo.pending_auto_apply_failed",
                payload={"error_code": err.code},
            )
        except Exception:
            await db.rollback()
            log_event(
                "promo.pending_auto_apply_failed",
                payload={"error_code": "UNEXPECTED"},
            )

    return result
# END_BLOCK: ROUTE_PROFILE_PUT
