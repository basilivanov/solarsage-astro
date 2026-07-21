# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_BILLING_NATAL_GATE — natal payment gate tests.
# ROLE: Proves the payment gate before natal full-report generation: 402
#       before entitlement, generation proceeds after a fulfilled natal
#       purchase; repeat generation of the purchased context stays free.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-BILLING-NATAL-GATE
# purpose: Directed tests for the natal entitlement gate in generate_report.
# owns:
#   - apps/api/tests/test_billing_natal_gate.py
# inputs: test DB session, mocked context/LLM, monkeypatched settings.
# outputs: 402 before purchase, success after entitlement, free repeat.
# dependencies: NatalReportService, BillingService entitlement rows.
# side_effects: test DB rows only.
# emitted_logs: none.
# invariants:
#   - Gate active only when YOOKASSA is enabled; no live provider calls.
# failure_policy: assertion failure.
# END_MODULE_CONTRACT: M-TESTS-BILLING-NATAL-GATE

from __future__ import annotations

import uuid
from datetime import date as Date, time as dtime
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock, patch

import json
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.config import settings
from app.db.models import NatalChartCache, Purchase, User, UserProfile
from app.db.session import Base
from app.services.natal_report_service import NatalReportService
from app.services.natal_context_service import NatalContextData, NatalChartPlanet, NatalChartHouse, NatalChartAngle

PROFILE_HASH = "gatehash-1"


def _mock_context() -> NatalContextData:
    return NatalContextData(
        planets=[
            NatalChartPlanet(name="Sun", sign="Capricorn", degree=16.9, house=11, longitude=286.9, retrograde=False),
            NatalChartPlanet(name="Moon", sign="Gemini", degree=29.6, house=4, longitude=119.6, retrograde=False),
        ],
        houses=[
            NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30))
            for i in range(1, 13)
        ],
        aspects=[],
        angles=[NatalChartAngle(name="ASC", sign="Pisces", degree=11.9, longitude=341.9)],
    )


def _valid_llm_json() -> str:
    return json.dumps({
        "blocks": [
            {"type": "lead", "text": "Главный вывод раздела длиной больше шестидесяти символов"},
            {"type": "paragraph", "text": "Развёрнутый абзац анализа длиной больше шестидесяти символов"},
            {"type": "callout", "title": "Совет", "text": "Практический совет длиной больше шестидесяти символов", "tone": "insight"},
        ]
    }, ensure_ascii=False)


async def _prepare():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    session = factory()
    user_id = uuid.uuid4()
    session.add(User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18)))
    session.add(
        UserProfile(
            user_id=user_id, first_name="Gate", gender="female",
            birthday=Date(1993, 1, 7), birth_time=dtime(10, 33),
            birth_city="Chirchiq", birth_lat=Decimal("41.46890"),
            birth_lon=Decimal("69.58220"), birth_tz="Asia/Tashkent",
            is_onboarded=True,
        )
    )
    session.add(
        NatalChartCache(
            user_id=user_id, profile_hash=PROFILE_HASH,
            raw_chart_json="{}", normalized_context_json="{}",
        )
    )
    await session.commit()
    return engine, session, user_id


@pytest.mark.asyncio
async def test_generate_requires_payment_before_entitlement(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    engine, session, user_id = await _prepare()
    service = NatalReportService(session)

    with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc:
        mock_instance = AsyncMock()
        mock_instance.get_or_build_natal_context.return_value = _mock_context()
        MockCtxSvc.return_value = mock_instance
        MockCtxSvc.compute_profile_hash = MagicMock(return_value=PROFILE_HASH)

        with pytest.raises(HTTPException) as excinfo:
            await service.generate_report(user_id)

    assert excinfo.value.status_code == 402
    assert excinfo.value.detail["code"] == "NATAL_PAYMENT_REQUIRED"
    await engine.dispose()


@pytest.mark.asyncio
async def test_generate_succeeds_after_entitlement_and_repeat_is_free(monkeypatch) -> None:
    monkeypatch.setattr(settings, "yookassa_enabled", True)
    engine, session, user_id = await _prepare()

    # Fulfilled natal entitlement for the current context.
    session.add(
        Purchase(
            user_id=user_id,
            product_slug="natal_full_report",
            status="delivered",
            context_hash=PROFILE_HASH,
        )
    )
    await session.commit()

    service = NatalReportService(session)
    with patch("app.services.natal_report_service.NatalContextService") as MockCtxSvc, \
         patch("app.services.llm_service.LLMService") as MockLLM:
        mock_instance = AsyncMock()
        mock_instance.get_or_build_natal_context.return_value = _mock_context()
        MockCtxSvc.return_value = mock_instance
        MockCtxSvc.compute_profile_hash = MagicMock(return_value=PROFILE_HASH)

        mock_llm = AsyncMock()
        mock_llm._generate_text.return_value = _valid_llm_json()
        MockLLM.return_value = mock_llm

        first = await service.generate_report(user_id)
        assert first.status in ("READY", "GENERATING")

        # Repeat generation of the purchased context stays free (idempotent
        # return of the same report, no 402).
        second = await service.generate_report(user_id)
        assert second.status in ("READY", "GENERATING")
        assert second.report_id == first.report_id

    await engine.dispose()
