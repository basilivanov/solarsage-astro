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
