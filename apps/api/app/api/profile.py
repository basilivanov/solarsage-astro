# ############################################################################
# AI_HEADER: MODULE_API_PROFILE
# ROLE: HTTP surface for /api/profile (GET, PUT). Owns UC-PROFILE-EDIT.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.profile_service
# GRACE_ANCHORS: [ROUTE_PROFILE_GET, ROUTE_PROFILE_PUT]
# ############################################################################

# START_MODULE_CONTRACT: M-PROFILE.api
# purpose: GET /api/profile returns ProfileRead; PUT /api/profile applies a
#   partial update. On any successful PUT the profile_service marks the user
#   cache-dirty (no-op marker in W-1.2; W-CACHE wires real invalidation).
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
# invariants:
#   - GET on a brand-new user lazily creates an empty profile row; never 404.
#   - PUT is partial: omitted fields stay as-is.
#   - Response NEVER carries tg_user_id / token_hash / other privacy keys.
# failure_policy:
#   - 401 propagates from current_user_id
#   - 422 from FastAPI on invalid body shape (Pydantic validators)
# non_goals:
#   - no audit log (W-1.6 retrofit)
# END_MODULE_CONTRACT: M-PROFILE.api

# START_MODULE_MAP: M-PROFILE.api
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_PROFILE_GET: GET /api/profile handler
#   - ROUTE_PROFILE_PUT: PUT /api/profile handler
# owned_tests:
#   - apps/api/tests/test_profile_endpoints.py
# END_MODULE_MAP: M-PROFILE.api

from __future__ import annotations

import uuid
from decimal import Decimal

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user_id
from app.db.models import UserProfile
from app.db.session import get_session
from app.schemas.profile import BirthData, ProfileRead, ProfileWrite
from app.services.profile_service import read_profile, update_profile

router = APIRouter()


def _to_read(profile: UserProfile) -> ProfileRead:
    return ProfileRead(
        user_id=profile.user_id,
        first_name=profile.first_name,
        birth=BirthData(
            birthday=profile.birthday,
            birth_time=profile.birth_time,
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
    )


# START_BLOCK: ROUTE_PROFILE_GET
@router.get("/api/profile", response_model=ProfileRead)
async def get_profile(
    user_id: uuid.UUID = Depends(current_user_id),
    db: AsyncSession = Depends(get_session),
) -> ProfileRead:
    profile = await read_profile(db, user_id)
    await db.commit()
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
    profile = await update_profile(db, user_id, body)
    await db.commit()
    # TODO(W-1.6): log.event("profile.updated", {fields: list(...)} )
    return _to_read(profile)
# END_BLOCK: ROUTE_PROFILE_PUT
