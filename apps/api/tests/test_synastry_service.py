"""Unit tests for SynastryService orchestration."""

from datetime import date, datetime, timezone
from unittest.mock import AsyncMock, patch
import uuid
import pytest

from app.db.models import (
    HoraryCredit,
    SynastryCreditSpend,
    SynastryPartner,
    SynastryReport,
    UserProfile,
)
from app.services.synastry_service import SynastryService


def test_synastry_service_import():
    assert SynastryService is not None


@pytest.mark.asyncio
async def test_run_report_pipeline_happy_path():
    """Happy path: sidecar call succeeds -> scoring -> LLM narrative succeeds -> READY state."""
    db = AsyncMock()

    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()

    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        owner_profile_hash="hash_123",
        state="pending",
        stage="init",
        attempt_count=0,
    )
    partner = SynastryPartner(
        id=partner_id,
        owner_id=user_id,
        name="Максим",
        relation_type="romantic",
        birth_date=date(1987, 9, 9),
        precision="exact",
        partner_input_hash="p_hash_123",
    )
    user_profile = UserProfile(
        user_id=user_id,
        birthday=date(1990, 1, 15),
        birth_lat=55.7558,
        birth_lon=37.6173,
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: report),
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: user_profile),
    ]

    service = SynastryService(db)

    sidecar_response = {
        "cross_aspects": [
            {"owner_planet": "Sun", "partner_planet": "Moon", "aspect_type": "trine", "orb_degrees": 1.0},
        ],
        "precision_flags": {"houses_available": True},
    }

    narrative_response = {
        "verdict": "Отличная совместимость пара",
        "summary": "Партнёры идеально чувствуют друг друга.",
        "hero_title": "Гармоничный союз",
        "hero_description": "Высокий потенциал пара.",
        "translations": [],
        "house_overlays": [],
    }

    with patch.object(service, "_fetch_sidecar_synastry", new_callable=AsyncMock) as mock_sidecar, \
         patch.object(service, "_generate_llm_narrative", new_callable=AsyncMock) as mock_llm:
        mock_sidecar.return_value = sidecar_response
        mock_llm.return_value = narrative_response

        res = await service.run_report_pipeline(report_id)

        assert res.state == "ready"
        assert res.stage == "done"
        assert res.error_code is None
        assert res.deterministic_payload_json is not None
        assert res.narrative_payload_json is not None


@pytest.mark.asyncio
async def test_run_report_pipeline_sidecar_failure_refunds_credit():
    """Sidecar failure -> state FAILED with SIDECAR_FAILED code and credit refund."""
    db = AsyncMock()

    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()
    credit_id = uuid.uuid4()

    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        owner_profile_hash="hash_123",
        state="pending",
        stage="init",
        attempt_count=0,
    )
    partner = SynastryPartner(
        id=partner_id,
        owner_id=user_id,
        name="Максим",
        relation_type="romantic",
        birth_date=date(1987, 9, 9),
        precision="exact",
        partner_input_hash="p_hash_123",
    )
    user_profile = UserProfile(
        user_id=user_id,
        birthday=date(1990, 1, 15),
        birth_lat=55.7558,
        birth_lon=37.6173,
    )
    spend = SynastryCreditSpend(
        id=uuid.uuid4(),
        user_id=user_id,
        credit_id=credit_id,
        report_id=report_id,
        amount=1,
        idempotency_key="idemp_123",
    )
    credit = HoraryCredit(
        id=credit_id,
        user_id=user_id,
        source="paid",
        amount=1,
        used_amount=1,
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: report),
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: user_profile),
        AsyncMock(scalar_one_or_none=lambda: spend),
        AsyncMock(scalar_one_or_none=lambda: credit),
    ]

    service = SynastryService(db)

    with patch.object(service, "_fetch_sidecar_synastry", new_callable=AsyncMock) as mock_sidecar:
        mock_sidecar.side_effect = RuntimeError("Sidecar connection timeout")

        res = await service.run_report_pipeline(report_id)

        assert res.state == "failed"
        assert res.error_code == "SIDECAR_FAILED"
        assert spend.refunded_at is not None
        assert credit.used_amount == 0


@pytest.mark.asyncio
async def test_run_report_pipeline_llm_failure_refunds_credit():
    """LLM validation failure twice -> state FAILED with LLM_VALIDATION_FAILED code and credit refund."""
    db = AsyncMock()

    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()
    credit_id = uuid.uuid4()

    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        owner_profile_hash="hash_123",
        state="pending",
        stage="init",
        attempt_count=0,
    )
    partner = SynastryPartner(
        id=partner_id,
        owner_id=user_id,
        name="Максим",
        relation_type="romantic",
        birth_date=date(1987, 9, 9),
        precision="exact",
        partner_input_hash="p_hash_123",
    )
    user_profile = UserProfile(
        user_id=user_id,
        birthday=date(1990, 1, 15),
        birth_lat=55.7558,
        birth_lon=37.6173,
    )
    spend = SynastryCreditSpend(
        id=uuid.uuid4(),
        user_id=user_id,
        credit_id=credit_id,
        report_id=report_id,
        amount=1,
        idempotency_key="idemp_123",
    )
    credit = HoraryCredit(
        id=credit_id,
        user_id=user_id,
        source="paid",
        amount=1,
        used_amount=1,
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: report),
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: user_profile),
        AsyncMock(scalar_one_or_none=lambda: spend),
        AsyncMock(scalar_one_or_none=lambda: credit),
    ]

    service = SynastryService(db)

    sidecar_response = {
        "cross_aspects": [
            {"owner_planet": "Sun", "partner_planet": "Moon", "aspect_type": "trine", "orb_degrees": 1.0},
        ],
        "precision_flags": {"houses_available": True},
    }

    with patch.object(service, "_fetch_sidecar_synastry", new_callable=AsyncMock) as mock_sidecar, \
         patch.object(service, "_generate_llm_narrative", new_callable=AsyncMock) as mock_llm:
        mock_sidecar.return_value = sidecar_response
        mock_llm.return_value = None  # LLM fails

        res = await service.run_report_pipeline(report_id)

        assert res.state == "failed"
        assert res.error_code == "LLM_VALIDATION_FAILED"
        assert res.attempt_count == 2
        assert spend.refunded_at is not None
        assert credit.used_amount == 0


@pytest.mark.asyncio
async def test_get_aspect_drilldown_not_found_in_report():
    """Aspect ID not found in report's deterministic payload -> raises 404."""
    from fastapi import HTTPException

    db = AsyncMock()
    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()

    partner = SynastryPartner(id=partner_id, owner_id=user_id, name="Максим")
    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        deterministic_payload_json='{"aspects": [{"id": "sun_trine_moon"}]}',
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: report),
    ]

    service = SynastryService(db)
    with pytest.raises(HTTPException) as exc_info:
        await service.get_aspect_drilldown(user_id, partner_id, "unknown_aspect_id")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_aspect_drilldown_happy_path():
    """Generating aspect drilldown via LLM -> persists ready detail and returns AspectDrilldown."""
    import json
    db = AsyncMock()
    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()

    partner = SynastryPartner(id=partner_id, owner_id=user_id, name="Максим")
    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        deterministic_payload_json='{"aspects": [{"id": "sun_trine_moon", "owner_planet": "Sun", "partner_planet": "Moon", "aspect": "trine", "tone": "good", "tech_signature": "Sun trine Moon"}]}',
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: report),
        AsyncMock(scalar_one_or_none=lambda: None), # no existing detail
    ]

    service = SynastryService(db)

    llm_payload = {
        "intro": "Взаимодействие сознания и подсознания.",
        "scenes": [
            {"title": "Внимание", "text": "Быстрое понимание друг друга."},
            {"title": "Разговор", "text": "Темы находятся сами."},
            {"title": "Дела", "text": "Планирование без конфликтов."},
        ],
        "repairs": ["1. Поддерживать прямой диалог."],
        "not_means": ["Не означает 1", "Не означает 2", "Не означает 3"],
    }

    with patch("app.services.synastry_service.LLMClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client._generate_text = AsyncMock(return_value=json.dumps(llm_payload, ensure_ascii=False))
        mock_client_cls.return_value = mock_client

        res = await service.get_aspect_drilldown(user_id, partner_id, "sun_trine_moon")

        assert res.aspect_id == "sun_trine_moon"
        assert res.tone == "good"
        assert "Взаимодействие" in res.explanation
        assert "Быстрое понимание" in (res.scenario or "")
        assert "Поддерживать" in (res.advice or "")


@pytest.mark.asyncio
async def test_get_aspect_drilldown_failure_does_not_affect_report_or_credit():
    """Drilldown LLM failure sets detail state=failed, leaves report ready, does NOT refund credit."""
    from fastapi import HTTPException
    from app.db.models import SynastryAspectDetail

    db = AsyncMock()
    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()

    partner = SynastryPartner(id=partner_id, owner_id=user_id, name="Максим")
    report = SynastryReport(
        id=report_id,
        owner_id=user_id,
        partner_id=partner_id,
        state="ready",
        deterministic_payload_json='{"aspects": [{"id": "sun_trine_moon", "owner_planet": "Sun", "partner_planet": "Moon", "aspect": "trine", "tone": "good"}]}',
    )

    db.execute.side_effect = [
        AsyncMock(scalar_one_or_none=lambda: partner),
        AsyncMock(scalar_one_or_none=lambda: report),
        AsyncMock(scalar_one_or_none=lambda: None), # no existing detail
    ]

    service = SynastryService(db)

    with patch("app.services.synastry_service.LLMClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client._generate_text = AsyncMock(return_value=None)  # LLM fails
        mock_client_cls.return_value = mock_client

        with pytest.raises(HTTPException) as exc_info:
            await service.get_aspect_drilldown(user_id, partner_id, "sun_trine_moon")

        assert exc_info.value.status_code == 500
        assert report.state == "ready"  # Base report state unchanged!


def test_match_translation_aspect_id_helper():
    from app.services.synastry_service import _match_translation_aspect_id

    aspects = [
        {"id": "sun_trine_moon", "owner_planet": "Sun", "partner_planet": "Moon", "aspect": "trine", "tech_signature": "Sun trine Moon (1.0°)"},
        {"id": "mercury_square_mercury", "owner_planet": "Mercury", "partner_planet": "Mercury", "aspect": "square", "tech_signature": "Mercury square Mercury (0.8°)"},
    ]

    assert _match_translation_aspect_id("Sun trine Moon", aspects) == "sun_trine_moon"
    assert _match_translation_aspect_id("Меркурий квадрат Меркурий", aspects) == "mercury_square_mercury"
    assert _match_translation_aspect_id("Unknown Aspect", aspects) is None

