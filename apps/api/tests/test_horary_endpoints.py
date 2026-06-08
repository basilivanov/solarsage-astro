from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.db.models import HoraryQuestion, HoraryQuota
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
async def test_get_quota_initial_state(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=42)
    r = await async_client.get("/api/horary/quota")
    assert r.status_code == 200
    body = r.json()
    assert body["left"] == 3
    assert body["nextInDays"] == 7
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
        },
    )
    assert r3.status_code == 422


@pytest.mark.asyncio
async def test_post_question_success_and_quota_consumption(
    async_client: AsyncClient, make_initdata
) -> None:
    await _login(async_client, make_initdata, user_id=45)

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
        }

        r = await async_client.post("/api/horary/questions", json=payload)
        assert r.status_code == 201
        body = r.json()
        assert body["text"] == "Will I find love this year?"
        assert body["category"] == "love"
        assert body["status"] == "processing"
        assert body["clientTimezone"] == "Europe/Moscow"
        assert body["clientLocalTime"] == "2026-06-08T14:32:00"

        # Check quota decremented
        r_quota = await async_client.get("/api/horary/quota")
        assert r_quota.status_code == 200
        assert r_quota.json()["left"] == 2


@pytest.mark.asyncio
async def test_quota_exceeded_returns_403(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    await _login(async_client, make_initdata, user_id=50)

    # Manually drain quota in DB
    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=50, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)
    
    service = HoraryService(db_session)
    quota = await service.get_or_create_quota(user.id)
    quota.questions_used = 3
    await db_session.commit()

    r = await async_client.post(
        "/api/horary/questions",
        json={
            "text": "Will I win the lottery?",
            "category": "money",
            "clientTimezone": "Europe/Moscow",
        },
    )
    assert r.status_code == 403
    assert r.json()["detail"] == "Horary quota exceeded"


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
    )
    db_session.add(question)
    await db_session.commit()

    # Attempt to GET as user 70
    r = await async_client.get(f"/api/horary/questions/{question.id}")
    assert r.status_code == 404
