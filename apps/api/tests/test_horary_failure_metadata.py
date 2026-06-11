
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_HORARY_FAILURE_METADATA
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for horary_failure_metadata.py behavior
# owns:
#   - apps/api/tests/test_horary_failure_metadata.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
from __future__ import annotations

import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from app.db.models import HoraryAnswer, HoraryCredit, HoraryQuestion, UserProfile
from app.schemas.horary import HoraryQuestionCreate
from app.services.horary_service import HoraryService
from app.services.llm_service import HoraryGenerationError


def _mock_chart() -> dict:
    return {
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


def _valid_blocks() -> list[dict]:
    return [
        {
            "type": "verdict_card",
            "verdict": "yes",
            "confidence": 0.8,
            "label": "Да",
            "confidenceLabel": "high",
            "confidenceExplanation": "Данных достаточно для уверенного вывода, потому что карта показывает несколько согласованных указаний без критичных противоречий.",
        },
        {
            "type": "lead",
            "text": "Ответ скорее положительный, потому что в карте сейчас преобладают поддерживающие указания и заметна согласованность факторов.",
        },
        {
            "type": "paragraph",
            "text": "Основные сигнификаторы описывают развитие без резких конфликтов, поэтому ситуация выглядит рабочей и допускает благоприятный исход при сохранении текущего курса.",
        },
        {
            "type": "testimonies",
            "prosLabel": "За",
            "consLabel": "Против",
            "neutralLabel": "Нейтрально",
            "pros": [
                {
                    "title": "Поддержка",
                    "explanation": "Есть заметное поддерживающее свидетельство, которое говорит в пользу благоприятного развития ситуации.",
                    "weight": 0.6,
                    "planets": ["Venus", "Saturn"],
                    "aspectType": "trine",
                    "orb": 1.2,
                }
            ],
            "cons": [],
            "neutral": [],
        },
        {
            "type": "paragraph",
            "text": "Ситуация может ослабнуть, если появятся новые ограничения или если участники начнут действовать менее последовательно, чем это видно сейчас.",
        },
        {
            "type": "timing",
            "status": "known",
            "timeRange": "1 неделя",
            "text": "Вероятное проявление видно в течение недели, потому что карта дает достаточно ясный и близкий временной ориентир.",
        },
        {
            "type": "callout",
            "tone": "insight",
            "title": "Совет",
            "text": "Лучше действовать спокойно и последовательно: закрепить имеющиеся преимущества, проверить детали и не форсировать естественный ход событий.",
        },
        {
            "type": "paragraph",
            "text": "Итог указывает на благоприятное развитие при сохранении текущей линии поведения и без лишнего давления на процесс.",
        },
    ]


@pytest.mark.asyncio
async def test_failed_question_has_failure_fields(db_session) -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    credit = HoraryCredit(user_id=user_id, source="paid", amount=1, used_amount=0)
    db_session.add_all([profile, credit])
    await db_session.commit()

    service = HoraryService(db_session)
    question, _ = await service.create_question(
        user_id,
        HoraryQuestionCreate(
            text="Will this fail?",
            category="career",
            client_timezone="UTC",
            idempotency_key="key-failure-metadata",
        ),
        datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
    )
    question_id = question.id
    await db_session.commit()

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch("app.services.horary_service.get_solarsage_client") as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class, patch(
        "app.services.horary_service.SessionLocal", _test_session_local
    ):
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = _mock_chart()
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.side_effect = HoraryGenerationError("thin answer")
        mock_llm_class.return_value = mock_llm

        await service._generate_answer_task(question_id)

    failed_question = (
        await db_session.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
    ).scalar_one()
    assert failed_question.status == "failed"
    assert failed_question.failure_stage == "llm_contract"
    assert failed_question.public_error_code == "GENERATION_FAILED"
    assert failed_question.public_error_message == "Не удалось построить ответ"


@pytest.mark.asyncio
async def test_answered_question_has_no_failure_fields(db_session) -> None:
    user_id = uuid.uuid4()
    profile = UserProfile(
        user_id=user_id,
        current_lat=Decimal("55.75"),
        current_lon=Decimal("37.62"),
    )
    credit = HoraryCredit(user_id=user_id, source="paid", amount=1, used_amount=0)
    db_session.add_all([profile, credit])
    await db_session.commit()

    service = HoraryService(db_session)
    question, _ = await service.create_question(
        user_id,
        HoraryQuestionCreate(
            text="Will this succeed?",
            category="career",
            client_timezone="UTC",
            idempotency_key="key-success-metadata",
        ),
        datetime(2026, 6, 9, 12, 0, tzinfo=timezone.utc),
    )
    question_id = question.id
    await db_session.commit()

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch("app.services.horary_service.get_solarsage_client") as mock_client_factory, patch(
        "app.services.horary_service.LLMService"
    ) as mock_llm_class, patch(
        "app.services.horary_service.SessionLocal", _test_session_local
    ):
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = _mock_chart()
        mock_client.get_transits.return_value = {"planets": []}
        mock_client_factory.return_value = mock_client

        mock_llm = AsyncMock()
        mock_llm.generate_horary_answer.return_value = {"blocks": _valid_blocks()}
        mock_llm_class.return_value = mock_llm

        await service._generate_answer_task(question_id)

    answered_question = (
        await db_session.execute(select(HoraryQuestion).where(HoraryQuestion.id == question_id))
    ).scalar_one()
    answer = (
        await db_session.execute(select(HoraryAnswer).where(HoraryAnswer.question_id == question_id))
    ).scalar_one()
    assert answered_question.status == "answered"
    assert answer is not None
    assert answered_question.failure_stage is None
    assert answered_question.public_error_code is None
    assert answered_question.public_error_message is None
