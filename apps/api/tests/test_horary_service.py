from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.db.models import HoraryQuestion, HoraryQuota, UserProfile
from app.schemas.horary import HoraryQuestionCreate
from app.schemas.normalization import AstroSignal
from app.services.horary_engine import HoraryEngine
from app.services.horary_service import HoraryService


def test_horary_engine_get_significator():
    assert HoraryEngine.get_significator("love") == "Venus"
    assert HoraryEngine.get_significator("career") == "Saturn"
    assert HoraryEngine.get_significator("money") == "Jupiter"
    assert HoraryEngine.get_significator("health") == "Mars"
    assert HoraryEngine.get_significator("travel") == "Mercury"
    assert HoraryEngine.get_significator("other") == "Moon"
    assert HoraryEngine.get_significator(None) == "Moon"


def test_horary_engine_compute_verdict_yes():
    # Good aspect (trine) between ASC ruler (Mars for Aries) and significator (Venus for love)
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],  # Aries (0-30 deg) -> ruler Mars
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = [
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Venus",
            aspect_type="trine",
            strength=0.9,
        ),
        AstroSignal(
            type="aspect",
            planet="Moon",
            target_planet="Sun",
            aspect_type="trine",
            strength=0.8,
        ),
    ]

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "yes"
    assert confidence > 0.5
    assert "Mars" in involved
    assert "Venus" in involved


def test_horary_engine_compute_verdict_no():
    # Bad aspect (opposition) between ASC ruler and significator
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = [
        AstroSignal(
            type="aspect",
            planet="Mars",
            target_planet="Venus",
            aspect_type="opposition",
            strength=0.9,
        )
    ]

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "no"
    assert confidence > 0.0


def test_horary_engine_compute_verdict_maybe():
    # No aspect
    horary_chart = {
        "special_points": [{"name": "ASC", "longitude": 10.0}],
        "planets": [{"name": "Moon", "longitude": 0.0}],
    }
    signals = []

    verdict, confidence, involved = HoraryEngine.compute_verdict(
        horary_chart, signals, "love"
    )
    assert verdict == "maybe"


@pytest.mark.asyncio
async def test_quota_get_or_create_and_reset(db_session) -> None:
    user_id = uuid.uuid4()
    service = HoraryService(db_session)

    # 1. First time creation
    quota = await service.get_or_create_quota(user_id)
    assert quota.questions_used == 0
    assert quota.questions_limit == 3
    assert (quota.reset_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days == 6

    # 2. Consume questions
    quota.questions_used = 3
    await db_session.commit()

    # 3. Simulate quota reset (reset_at in the past)
    quota.reset_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    # Call get_or_create_quota again to trigger auto-reset
    quota2 = await service.get_or_create_quota(user_id)
    assert quota2.questions_limit == 4
    # Reset at should be reset to +7 days
    assert (quota2.reset_at.replace(tzinfo=timezone.utc) - datetime.now(timezone.utc)).days == 6


@pytest.mark.asyncio
async def test_check_quota(db_session) -> None:
    user_id = uuid.uuid4()
    service = HoraryService(db_session)

    # Starts with 3 available questions
    assert await service.check_quota(user_id) is True

    quota = await service.get_or_create_quota(user_id)
    quota.questions_used = 3
    await db_session.commit()

    # Quota depleted
    assert await service.check_quota(user_id) is False


@pytest.mark.asyncio
async def test_create_question_consumes_quota(db_session) -> None:
    user_id = uuid.uuid4()
    # Need user profile in DB for the background resolver fallback
    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    db_session.add(profile)
    await db_session.commit()

    service = HoraryService(db_session)
    data = HoraryQuestionCreate(
        text="Will I get a promotion?",
        category="career",
        client_timezone="Europe/Moscow",
    )

    question = await service.create_question(user_id, data)
    assert question.status == "processing"
    assert question.text == "Will I get a promotion?"

    quota = await service.get_or_create_quota(user_id)
    assert quota.questions_used == 1
