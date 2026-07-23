# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_FEEDBACK_SERVICE
# ROLE: Tests for FeedbackService and feedback_broadcast job.
# DEPENDENCIES: pytest, pytest-asyncio, app.services.feedback_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-FEEDBACK-SERVICE
# purpose: Test DayFeedback upsert/get, list_users_for_reminder, and broadcast job.
# owns:
#   - apps/api/tests/test_feedback_service.py
# inputs: db_session, FeedbackService
# outputs: pytest assertions
# END_MODULE_CONTRACT: M-TEST-FEEDBACK-SERVICE

from datetime import UTC, date, datetime, timedelta
import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile, EveningCheckin
from app.services.feedback_service import FeedbackService
from app.services.profile_service import get_or_create_user, read_profile
from app.services.telegram_auth import TelegramUser


@pytest.mark.asyncio
async def test_feedback_upsert_and_get(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=7770001, username="fb_user_1", first_name="Fb1")
    user, _ = await get_or_create_user(db_session, tg_user)

    service = FeedbackService(db_session)
    target_date = date(2026, 7, 22)

    # Initial upsert
    fb1 = await service.upsert(user.id, target_date, accuracy=3, source="tg_bot")
    assert fb1.accuracy == 3
    assert fb1.source == "tg_bot"

    # Idempotent / update upsert
    fb2 = await service.upsert(user.id, target_date, accuracy=1, source="webapp")
    assert fb2.id == fb1.id
    assert fb2.accuracy == 1
    assert fb2.source == "webapp"

    # Fetch
    fetched = await service.get_for_date(user.id, target_date)
    assert fetched is not None
    assert fetched.accuracy == 1


@pytest.mark.asyncio
async def test_feedback_invalid_accuracy(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=7770002, username="fb_user_2", first_name="Fb2")
    user, _ = await get_or_create_user(db_session, tg_user)

    service = FeedbackService(db_session)
    target_date = date(2026, 7, 22)

    with pytest.raises(ValueError):
        await service.upsert(user.id, target_date, accuracy=0)

    with pytest.raises(ValueError):
        await service.upsert(user.id, target_date, accuracy=4)


@pytest.mark.asyncio
async def test_list_users_for_reminder(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=7770003, username="fb_user_3", first_name="Fb3")
    user, _ = await get_or_create_user(db_session, tg_user)
    profile = await read_profile(db_session, user.id)

    profile.current_tz = "UTC"
    profile.is_onboarded = True
    await db_session.flush()

    service = FeedbackService(db_session)
    # Simulate now_utc = 2026-07-23 20:15:00 UTC (hour 20)
    now_utc = datetime(2026, 7, 23, 20, 15, 0, tzinfo=UTC)

    users = await service.list_users_for_reminder(target_hour_local=20, now_utc=now_utc)
    assert any(u.id == user.id for u in users)

    # If user already gave feedback for local yesterday (2026-07-22), should be excluded
    await service.upsert(user.id, date(2026, 7, 22), accuracy=2)
    users_after_fb = await service.list_users_for_reminder(target_hour_local=20, now_utc=now_utc)
    assert not any(u.id == user.id for u in users_after_fb)
