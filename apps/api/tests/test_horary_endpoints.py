from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch
from sqlalchemy import select
from decimal import Decimal

import pytest
from httpx import AsyncClient

from app.db.models import HoraryQuestion, HoraryCredit, UserProfile
from app.services.horary_service import HoraryService


async def _login(async_client: AsyncClient, make_initdata, *, user_id: int = 42) -> None:
    raw = make_initdata(user_id=user_id, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_horary_requires_session(async_client: AsyncClient) -> None:
    r = await async_client.get("/api/horary/quota")
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_get_quota_initial_state_no_access(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.get("/api/horary/quota")
    assert r.status_code == 200
    body = r.json()
    assert body["weeklyFreeAvailable"] is False
    assert body["weeklyFreeExpiresAt"] is None
    assert body["bonusCredits"] == 0
    assert body["paidCredits"] == 0
    assert body["canPurchase"] is True


@pytest.mark.asyncio
async def test_post_question_validation_errors(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)

    # Text too short
    r = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "abcd",
            "category": "love",
            "clientTimezone": "Europe/Moscow",
            "idempotencyKey": "key-val-err",
        },
    )
    assert r.status_code == 422

    # Text too long (501 chars)
    r3 = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "a" * 501,
            "category": "love",
            "clientTimezone": "Europe/Moscow",
            "idempotencyKey": "key-val-err",
        },
    )
    assert r3.status_code == 422

    # Missing idempotencyKey
    r4 = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "Valid question text?",
            "category": "love",
            "clientTimezone": "Europe/Moscow",
        },
    )
    assert r4.status_code == 422


@pytest.mark.asyncio
async def test_post_question_success_and_credit_consumption(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=45)

    # Resolve user
    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=45, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    # Setup profile lat/lon
    from app.db.models import UserProfile
    from decimal import Decimal
    from sqlalchemy import select
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")
    profile.birth_lat = Decimal("55.75")
    profile.birth_lon = Decimal("37.62")

    # Give user a paid credit
    credit = HoraryCredit(
        user_id=user.id,
        source="paid",
        amount=1,
        used_amount=0,
    )
    db_session.add(credit)
    await db_session.commit()

    # Mock sidecar + LLM so it doesn't fail background task
    with patch(
        "app.services.horary_service.get_solarsage_client"
    ) as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = {
            "planets": [
                {"name": "Sun", "longitude": 0.0, "latitude": 0.0, "speed": 1.0, "sign": "Aries"},
                {"name": "Moon", "longitude": 30.0, "latitude": 0.0, "speed": 1.0, "sign": "Taurus"},
                {"name": "Venus", "longitude": 60.0, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
            ],
            "special_points": [{"name": "ASC", "longitude": 0.0}],
        }
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.return_value = {
            "blocks": [
                {"type": "verdict_card", "verdict": "yes", "confidence": 0.8, "label": "Да"}
            ]
        }
        mock_llm_class.return_value = mock_llm

        payload = {
            "text": "Will I find love this year?",
            "category": "love",
            "clientTimezone": "Europe/Moscow",
            "clientLocalTime": "2026-06-08T14:32:00",
            "questionLat": 55.75,
            "questionLon": 37.62,
            "idempotencyKey": "key-success-endpoint",
        }

        r = await async_client.post("/api/horary/questions", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["text"] == "Will I find love this year?"
        assert body["category"] == "love"
        assert body["status"] == "processing"
        assert body["clientTimezone"] == "Europe/Moscow"
        assert body["clientLocalTime"] == "2026-06-08T14:32:00"
        assert body["spentCreditSource"] == "paid"

        # Check quota decremented
        r_quota = await async_client.get("/api/horary/quota")
        assert r_quota.status_code == 200
        assert r_quota.json()["paidCredits"] == 0


@pytest.mark.asyncio
async def test_no_credits_returns_402(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=50)

    # Attempt to post a question without any credits
    r = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "Will I win the lottery?",
            "category": "money",
            "clientTimezone": "Europe/Moscow",
            "idempotencyKey": "key-insufficient-credits",
        },
    )
    assert r.status_code == 402
    assert r.json()["detail"] == "NO_HORARY_CREDITS"


@pytest.mark.asyncio
async def test_idempotency_conflict_returns_409(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=55)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=55, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    # Add credits
    credit = HoraryCredit(user_id=user.id, source="paid", amount=5, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    # Post first time
    r1 = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "Will I get a promotion?",
            "category": "career",
            "clientTimezone": "Europe/Moscow",
            "idempotencyKey": "key-dup-endpoint",
        },
    )
    assert r1.status_code == 201

    # Post second time with different text -> 409
    r2 = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "Will I get rich instead?",
            "category": "money",
            "clientTimezone": "Europe/Moscow",
            "idempotencyKey": "key-dup-endpoint",
        },
    )
    assert r2.status_code == 409
    assert r2.json()["detail"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_get_questions_list_and_details(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=60)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=60, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    # Insert fake answered question
    question = HoraryQuestion(
        id=uuid.uuid4(),
        user_id=user.id,
        text="Will my project succeed?",
        category="career",
        status="answered",
        client_timezone="Europe/Moscow",
        idempotency_key="key-list",
        request_hash="hash-list",
    )
    db_session.add(question)
    await db_session.flush()

    # Fake answer
    answer = HoraryQuestion.__mapper__.relationships["answer"].mapper.class_(
        question_id=question.id,
        verdict="yes",
        confidence=0.9,
        blocks_json='[{"type": "paragraph", "text": "Everything looks great!"}]',
        planets_json='["Sun", "Jupiter"]',
    )
    db_session.add(answer)
    await db_session.commit()

    # List questions
    r_list = await async_client.get("/api/horary/questions")
    assert r_list.status_code == 200
    list_body = r_list.json()
    assert len(list_body) == 1
    assert list_body[0]["id"] == str(question.id)
    assert list_body[0]["answer"]["verdict"] == "yes"

    # Details
    r_det = await async_client.get(f"/api/horary/questions/{question.id}")
    assert r_det.status_code == 200
    det_body = r_det.json()
    assert det_body["text"] == "Will my project succeed?"
    assert len(det_body["answer"]["blocks"]) == 1
    assert det_body["answer"]["blocks"][0]["text"] == "Everything looks great!"


@pytest.mark.asyncio
async def test_get_foreign_question_returns_404(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    # Login as user 70
    await _login(async_client, make_initdata, user_id=70)
    
    # Create question for user 75
    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=75, username="bob", first_name="Bob")
    user, _ = await get_or_create_user(db_session, tg)

    question = HoraryQuestion(
        id=uuid.uuid4(),
        user_id=user.id,
        text="Is it a good question?",
        client_timezone="UTC",
        idempotency_key="key-foreign",
        request_hash="hash-foreign",
    )
    db_session.add(question)
    await db_session.commit()

    # Attempt to GET as user 70
    r = await async_client.get(f"/api/horary/questions/{question.id}")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_duplicate_same_payload_returns_existing_and_does_not_enqueue_twice(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=85)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=85, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    # Setup profile
    from app.db.models import UserProfile
    from decimal import Decimal
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")
    
    # Give user 2 paid credits
    credit = HoraryCredit(user_id=user.id, source="paid", amount=2, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    payload = {
        "text": "Will I find my wallet?",
        "category": "other",
        "clientTimezone": "UTC",
        "clientLocalTime": "2026-06-08T15:00:00",
        "idempotencyKey": "key-idempotency-twice",
    }

    # Patch create_task
    with patch("app.api.horary.asyncio.create_task") as mock_create_task:
        r1 = await async_client.post("/api/horary/questions", json=payload)
        assert r1.status_code == 201
        body1 = r1.json()

        r2 = await async_client.post("/api/horary/questions", json=payload)
        assert r2.status_code == 201
        body2 = r2.json()

        assert body1["id"] == body2["id"]
        # Background task should be enqueued ONLY once
        assert mock_create_task.call_count == 1

        # Only 1 credit spent
        await db_session.refresh(credit)
        assert credit.used_amount == 1


@pytest.mark.asyncio
async def test_same_idempotency_key_different_client_time_returns_409(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=90)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=90, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    credit = HoraryCredit(user_id=user.id, source="paid", amount=2, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    payload1 = {
        "text": "Will I buy a car?",
        "category": "money",
        "clientTimezone": "UTC",
        "clientLocalTime": "2026-06-08T15:00:00",
        "idempotencyKey": "key-time-diff",
    }

    payload2 = {
        "text": "Will I buy a car?",
        "category": "money",
        "clientTimezone": "UTC",
        "clientLocalTime": "2026-06-08T15:30:00",  # changed time
        "idempotencyKey": "key-time-diff",
    }

    r1 = await async_client.post("/api/horary/questions", json=payload1)
    assert r1.status_code == 201

    r2 = await async_client.post("/api/horary/questions", json=payload2)
    assert r2.status_code == 409
    assert r2.json()["detail"] == "IDEMPOTENCY_CONFLICT"


@pytest.mark.asyncio
async def test_same_idempotency_key_different_location_returns_409(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=95)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=95, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    credit = HoraryCredit(user_id=user.id, source="paid", amount=2, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    payload1 = {
        "text": "Will I travel to Paris?",
        "category": "travel",
        "clientTimezone": "UTC",
        "clientLocalTime": "2026-06-08T15:00:00",
        "questionLat": 55.75,
        "questionLon": 37.62,
        "idempotencyKey": "key-loc-diff",
    }

    payload2 = {
        "text": "Will I travel to Paris?",
        "category": "travel",
        "clientTimezone": "UTC",
        "clientLocalTime": "2026-06-08T15:00:00",
        "questionLat": 48.85,  # changed location
        "questionLon": 2.35,
        "idempotencyKey": "key-loc-diff",
    }

    r1 = await async_client.post("/api/horary/questions", json=payload1)
    assert r1.status_code == 201

    r2 = await async_client.post("/api/horary/questions", json=payload2)
    assert r2.status_code == 409
    assert r2.json()["detail"] == "IDEMPOTENCY_CONFLICT"
