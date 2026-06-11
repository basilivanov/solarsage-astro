
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_HORARY_ENDPOINTS
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_horary_endpoints.py
# owns:
#   - apps/api/tests/test_horary_endpoints.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
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


@pytest.mark.asyncio
async def test_llm_invalid_json_marks_question_failed_and_no_answer_saved(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 §4.4 / §6.1.

    When LLM JSON is invalid the service must mark the question failed and
    not save a HoraryAnswer row. The credit is refunded.
    """
    await _login(async_client, make_initdata, user_id=110)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=110, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    from app.db.models import UserProfile, HoraryAnswer
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch(
        "app.services.horary_service.get_solarsage_client"
    ) as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class, patch(
        "app.services.horary_service.SessionLocal", _test_session_local
    ), patch(
        "app.api.horary.asyncio.create_task"
    ):
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = {
            "planets": [
                {"name": "Sun", "longitude": 0.0, "latitude": 0.0, "speed": 1.0, "sign": "Aries"},
                {"name": "Moon", "longitude": 30.0, "latitude": 0.0, "speed": 1.0, "sign": "Taurus"},
                {"name": "Venus", "longitude": 60.0, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Saturn", "longitude": 90.0, "latitude": 0.0, "speed": 0.05, "sign": "Cancer"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0}, {"number": 2, "cusp": 30.0},
                {"number": 3, "cusp": 60.0}, {"number": 4, "cusp": 90.0},
                {"number": 5, "cusp": 120.0}, {"number": 6, "cusp": 150.0},
                {"number": 7, "cusp": 180.0}, {"number": 8, "cusp": 210.0},
                {"number": 9, "cusp": 240.0}, {"number": 10, "cusp": 270.0},
                {"number": 11, "cusp": 300.0}, {"number": 12, "cusp": 330.0},
            ],
            "special_points": [{"name": "ASC", "longitude": 0.0}],
        }
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        from app.services.llm_service import HoraryGenerationError
        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.side_effect = HoraryGenerationError("bad json")
        mock_llm_class.return_value = mock_llm

        payload = {
            "text": "Will the meeting succeed tomorrow?",
            "category": "career",
            "clientTimezone": "UTC",
            "clientLocalTime": "2026-06-08T15:00:00",
            "idempotencyKey": "key-llm-bad-json",
        }
        r = await async_client.post("/api/horary/questions", json=payload)
        assert r.status_code == 201
        qid = r.json()["id"]
        qid_uuid = uuid.UUID(qid)

        from app.services.horary_service import HoraryService
        svc = HoraryService(db_session)
        await svc._generate_answer_task(qid_uuid)

        q_row = (await db_session.execute(select(HoraryQuestion).where(HoraryQuestion.id == qid_uuid))).scalar_one()
        assert q_row.status == "failed"

        answer_count = (await db_session.execute(
            select(HoraryAnswer).where(HoraryAnswer.question_id == qid_uuid)
        )).all()
        assert len(answer_count) == 0

        await db_session.refresh(credit)
        assert credit.used_amount == 0

        r2 = await async_client.get(f"/api/horary/questions/{qid}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "failed"
        assert body["creditRefunded"] is True
        assert body["answer"] is None


@pytest.mark.asyncio
async def test_llm_unavailable_marks_question_failed_and_refunds_credit(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 §6.2: LLM unavailable => failed + refund."""
    await _login(async_client, make_initdata, user_id=120)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=120, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    from app.db.models import UserProfile, HoraryAnswer
    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch(
        "app.services.horary_service.get_solarsage_client"
    ) as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class, patch(
        "app.services.horary_service.SessionLocal", _test_session_local
    ), patch(
        "app.api.horary.asyncio.create_task"
    ):
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = {
            "planets": [
                {"name": "Sun", "longitude": 0.0, "latitude": 0.0, "speed": 1.0, "sign": "Aries"},
                {"name": "Moon", "longitude": 30.0, "latitude": 0.0, "speed": 1.0, "sign": "Taurus"},
                {"name": "Venus", "longitude": 60.0, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Jupiter", "longitude": 90.0, "latitude": 0.0, "speed": 0.05, "sign": "Cancer"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0}, {"number": 2, "cusp": 30.0},
                {"number": 3, "cusp": 60.0}, {"number": 4, "cusp": 90.0},
                {"number": 5, "cusp": 120.0}, {"number": 6, "cusp": 150.0},
                {"number": 7, "cusp": 180.0}, {"number": 8, "cusp": 210.0},
                {"number": 9, "cusp": 240.0}, {"number": 10, "cusp": 270.0},
                {"number": 11, "cusp": 300.0}, {"number": 12, "cusp": 330.0},
            ],
            "special_points": [{"name": "ASC", "longitude": 0.0}],
        }
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        from app.services.llm_service import HoraryGenerationError
        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.side_effect = HoraryGenerationError("LLM provider down")
        mock_llm_class.return_value = mock_llm

        payload = {
            "text": "Will the deal close this quarter?",
            "category": "money",
            "clientTimezone": "UTC",
            "clientLocalTime": "2026-06-08T15:00:00",
            "idempotencyKey": "key-llm-unavail",
        }
        r = await async_client.post("/api/horary/questions", json=payload)
        assert r.status_code == 201
        qid = r.json()["id"]
        qid_uuid = uuid.UUID(qid)

        from app.services.horary_service import HoraryService
        svc = HoraryService(db_session)
        await svc._generate_answer_task(qid_uuid)

        q_row = (await db_session.execute(select(HoraryQuestion).where(HoraryQuestion.id == qid_uuid))).scalar_one()
        assert q_row.status == "failed"
        await db_session.refresh(credit)
        assert credit.used_amount == 0
        answers = (await db_session.execute(
            select(HoraryAnswer).where(HoraryAnswer.question_id == qid_uuid)
        )).all()
        assert len(answers) == 0


@pytest.mark.asyncio
async def test_no_probability_wording_in_horary_answer_payload(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 §6.6: API contract does not emit
    probability wording in user-facing horary payloads."""
    from app.schemas.horary import VerdictCardBlock, HoraryAnswerRead

    block = VerdictCardBlock(
        verdict="yes",
        confidence=0.5,
        label="Да",
        confidenceLabel="medium",
        confidenceExplanation="x",
    )
    answer = HoraryAnswerRead(
        verdict="yes",
        confidence=0.5,
        confidenceLabel="medium",
        confidenceExplanation="x",
        blocks=[block],
        planets=["Sun"],
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
    raw = answer.model_dump(by_alias=True)
    s = json.dumps(raw, ensure_ascii=False)
    assert "вероятность" not in s.lower()
    assert "55%" not in s
    assert "65%" not in s


@pytest.mark.asyncio
async def test_credit_refunded_true_for_paid_credit_on_failure(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 followup §B2: paid credit failure
    => API reports creditRefunded=true."""
    await _login(async_client, make_initdata, user_id=210)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=210, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch(
        "app.services.horary_service.get_solarsage_client"
    ) as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class, patch(
        "app.services.horary_service.SessionLocal", _test_session_local
    ), patch(
        "app.api.horary.asyncio.create_task"
    ):
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = {
            "planets": [
                {"name": "Sun", "longitude": 0.0, "latitude": 0.0, "speed": 1.0, "sign": "Aries"},
                {"name": "Moon", "longitude": 30.0, "latitude": 0.0, "speed": 1.0, "sign": "Taurus"},
                {"name": "Venus", "longitude": 60.0, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Saturn", "longitude": 90.0, "latitude": 0.0, "speed": 0.05, "sign": "Cancer"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0}, {"number": 2, "cusp": 30.0},
                {"number": 3, "cusp": 60.0}, {"number": 4, "cusp": 90.0},
                {"number": 5, "cusp": 120.0}, {"number": 6, "cusp": 150.0},
                {"number": 7, "cusp": 180.0}, {"number": 8, "cusp": 210.0},
                {"number": 9, "cusp": 240.0}, {"number": 10, "cusp": 270.0},
                {"number": 11, "cusp": 300.0}, {"number": 12, "cusp": 330.0},
            ],
            "special_points": [{"name": "ASC", "longitude": 0.0}],
        }
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        from app.services.llm_service import HoraryGenerationError
        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.side_effect = HoraryGenerationError("bad json")
        mock_llm_class.return_value = mock_llm

        payload = {
            "text": "Will the deal close?",
            "category": "career",
            "clientTimezone": "UTC",
            "clientLocalTime": "2026-06-08T15:00:00",
            "idempotencyKey": "key-paid-refund-flag",
        }
        r = await async_client.post("/api/horary/questions", json=payload)
        assert r.status_code == 201
        qid = r.json()["id"]
        qid_uuid = uuid.UUID(qid)

        from app.services.horary_service import HoraryService
        svc = HoraryService(db_session)
        await svc._generate_answer_task(qid_uuid)

        r2 = await async_client.get(f"/api/horary/questions/{qid}")
        assert r2.status_code == 200
        body = r2.json()
        assert body["status"] == "failed"
        assert body["creditRefunded"] is True


@pytest.mark.asyncio
async def test_credit_refunded_false_for_expired_weekly_free_on_failure(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """W-HORARY-ANSWER-QUALITY-V1 followup §B2: expired weekly-free
    failure => creditRefunded must be false (no actual refund happened)."""
    await _login(async_client, make_initdata, user_id=220)

    from app.services.telegram_auth import TelegramUser
    from app.services.profile_service import get_or_create_user
    tg = TelegramUser(id=220, username="ada", first_name="Ada")
    user, _ = await get_or_create_user(db_session, tg)

    profile = (await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))).scalar_one()
    profile.current_lat = Decimal("55.75")
    profile.current_lon = Decimal("37.62")

    # Pre-create a weekly-free credit whose access_week_end is in the past
    expired_credit = HoraryCredit(
        user_id=user.id,
        source="subscription_weekly_free",
        amount=1,
        used_amount=0,
        access_week_start=datetime(2026, 5, 25, 0, 0, tzinfo=timezone.utc),
        access_week_end=datetime(2026, 6, 1, 0, 0, tzinfo=timezone.utc),
    )
    db_session.add(expired_credit)
    await db_session.commit()

    from datetime import datetime as _dt
    from app.db.models import HoraryCreditSpend
    import hashlib
    payload_json = json.dumps(
        {"text": "Will I win?", "category": "other", "client_timezone": "UTC"},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    request_hash = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()
    now = _dt(2026, 6, 9, 12, 0, tzinfo=timezone.utc)
    question = HoraryQuestion(
        id=uuid.uuid4(),
        user_id=user.id,
        text="Will I win?",
        category="other",
        status="processing",
        client_timezone="UTC",
        idempotency_key="key-expired-week-endpoint",
        request_hash=request_hash,
        spent_credit_id=expired_credit.id,
    )
    db_session.add(question)
    spend = HoraryCreditSpend(
        user_id=user.id,
        credit_id=expired_credit.id,
        question_id=question.id,
        amount=1,
        idempotency_key="key-expired-week-endpoint",
    )
    db_session.add(spend)
    expired_credit.used_amount = 1
    await db_session.commit()

    from app.services.horary_service import HoraryService
    svc = HoraryService(db_session)
    question.status = "failed"
    await db_session.flush()
    await svc._refund_credit_for_failed_question(db_session, question.id, now)
    await db_session.commit()

    r = await async_client.get(f"/api/horary/questions/{question.id}")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "failed"
    assert body["creditRefunded"] is False
