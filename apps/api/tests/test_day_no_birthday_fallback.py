# ############################################################################
# AI_HEADER: M-TEST-DAY-NO-BIRTHDAY-FALLBACK — day/no-birthday-fallback behavior.
# ROLE: Tests for the day onboarding gate and preserved TodayService validation.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-NO-BIRTHDAY-FALLBACK
# purpose: Tests for the day onboarding gate and preserved TodayService
#   missing-coordinate validation.
# owns:
#   - apps/api/tests/test_day_no_birthday_fallback.py
# inputs: DB fixture, test client, init data generator.
# outputs: Assertion evidence.
# dependencies: test fixtures, app models/services, mock sidecar data.
# side_effects: DB reads/writes, API calls via test client.
# emitted_logs: none.
# invariants: none.
# failure_policy: AssertionError on test failure.
# END_MODULE_CONTRACT: M-TEST-DAY-NO-BIRTHDAY-FALLBACK

# START_MODULE_MAP: M-TEST-DAY-NO-BIRTHDAY-FALLBACK
# public_entrypoints:
#   - test_day_not_onboarded_without_birth_coords
#   - test_today_service_raises_without_birth_coords
# owned_tests:
#   - apps/api/tests/test_day_no_birthday_fallback.py
# END_MODULE_MAP: M-TEST-DAY-NO-BIRTHDAY-FALLBACK

from __future__ import annotations

import uuid
from datetime import date as Date
from decimal import Decimal

import pytest
from fastapi import HTTPException
from httpx import AsyncClient
from sqlalchemy import select

from app.db.models import User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService

from .test_horary_endpoints import _login


@pytest.mark.asyncio
async def test_day_not_onboarded_without_birth_coords(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-DAY-NO-BIRTHDAY-FALLBACK.test_day_not_onboarded_without_birth_coords
    # purpose: Verify 422 for onboarded-without-birth-coords profile.
    # inputs: async_client, make_initdata, db_session.
    # returns: none.
    # side_effects: DB write (profile fields), API GET /api/day/today.
    # emitted_logs: none.
    # error_behavior: AssertionError on unexpected status or body.
    # END_FUNCTION_CONTRACT: F-M-TEST-DAY-NO-BIRTHDAY-FALLBACK.test_day_not_onboarded_without_birth_coords
    await _login(async_client, make_initdata, user_id=401)

    user_id = (
        await db_session.execute(select(User.id).where(User.tg_user_id == 401))
    ).scalar_one()
    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user_id))
    ).scalar_one()
    profile.is_onboarded = True
    profile.birthday = Date(1990, 6, 15)
    profile.birth_tz = "Europe/Moscow"
    profile.birthday_lat = Decimal("55.75580")
    profile.birthday_lon = Decimal("37.61730")
    profile.birth_lat = None
    profile.birth_lon = None
    await db_session.commit()

    r = await async_client.get("/api/day/today")
    assert r.status_code == 422
    assert r.json()["detail"]["code"] == "NOT_ONBOARDED"


@pytest.mark.asyncio
async def test_today_service_raises_without_birth_coords(db_session) -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-DAY-NO-BIRTHDAY-FALLBACK.test_today_service_raises_without_birth_coords
    # purpose: Prove TodayService raises 409 when profile lacks birth coords.
    # inputs: db_session.
    # returns: none.
    # side_effects: DB write (profile without coords), direct service call.
    # emitted_logs: none.
    # error_behavior: HTTPException 409 with expected missing fields.
    # END_FUNCTION_CONTRACT: F-M-TEST-DAY-NO-BIRTHDAY-FALLBACK.test_today_service_raises_without_birth_coords
    user_id = uuid.uuid4()
    profile = UserProfile(
        user_id=user_id,
        birthday=Date(1990, 6, 15),
        birth_tz="Europe/Moscow",
        birth_lat=None,
        birth_lon=None,
        birthday_lat=Decimal("55.75580"),
        birthday_lon=Decimal("37.61730"),
    )
    db_session.add(profile)
    await db_session.commit()

    service = TodayService(db_session)
    access_state = ContentAccessState(
        state="full",
        reason="active_subscription",
        referralDaysLeft=None,
        subscriptionActive=None,
        accessUntil=None,
    )

    with pytest.raises(HTTPException) as exc:
        await service.get_today_payload(user_id, Date(2026, 6, 9), access_state)

    assert exc.value.status_code == 409
    assert exc.value.detail == {
        "message": "Birth coordinates are required",
        "missingFields": ["birth_lat", "birth_lon"],
    }
