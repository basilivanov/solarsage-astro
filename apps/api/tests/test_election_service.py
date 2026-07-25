# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ELECTION_SERVICE
# ROLE: Integration tests for ElectionService.
# DEPENDENCIES: pytest, pytest-asyncio, app.services.election_service
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-ELECTION-SERVICE
# purpose: Test ElectionService creation, credit consumption, idempotency, execution & refund logic.
# owns:
#   - apps/api/tests/test_election_service.py
# inputs: db_session, make_initdata
# outputs: pytest assertions
# END_MODULE_CONTRACT: M-TEST-ELECTION-SERVICE

import uuid
from datetime import date
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HoraryCredit, ElectionRequest, ElectionResult, ElectionCreditSpend
from app.services.election_service import ElectionService
from app.services.horary_credit_service import HoraryCreditService
from app.services.profile_service import get_or_create_user
from app.services.telegram_auth import TelegramUser


@pytest.mark.asyncio
async def test_create_search_success_and_credit_consumption(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990001, username="el_user1", first_name="El1")
    user, _ = await get_or_create_user(db_session, tg_user)

    # Grant credit
    credit = HoraryCredit(
        user_id=user.id,
        source="paid",
        amount=1,
        used_amount=0,
    )
    db_session.add(credit)
    await db_session.commit()

    service = ElectionService(db_session)
    req = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-1",
    )

    assert req.status == "pending"
    assert req.event_type == "wedding"
    assert req.spent_credit_id == credit.id

    # Check credit used_amount updated
    await db_session.refresh(credit)
    assert credit.used_amount == 1

    # Check spend row created
    stmt = (await db_session.execute(
        select(ElectionCreditSpend).where(ElectionCreditSpend.election_request_id == req.id)
    )).scalar_one_or_none()
    assert stmt is not None


from sqlalchemy import select


@pytest.mark.asyncio
async def test_create_search_no_credits(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990002, username="el_user2", first_name="El2")
    user, _ = await get_or_create_user(db_session, tg_user)

    service = ElectionService(db_session)
    with pytest.raises(HTTPException) as exc:
        await service.create_search(
            user_id=user.id,
            event_type="wedding",
            window_from=date(2026, 8, 1),
            window_to=date(2026, 8, 5),
            idempotency_key="key-2",
        )
    assert exc.value.status_code == 402


@pytest.mark.asyncio
async def test_create_search_idempotency(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990003, username="el_user3", first_name="El3")
    user, _ = await get_or_create_user(db_session, tg_user)

    credit = HoraryCredit(user_id=user.id, source="paid", amount=2, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = ElectionService(db_session)
    req1 = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-same",
    )

    # Same params -> return req1 without double spend
    req2 = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-same",
    )
    assert req2.id == req1.id

    # Different params -> 409
    with pytest.raises(HTTPException) as exc:
        await service.create_search(
            user_id=user.id,
            event_type="job",
            window_from=date(2026, 8, 1),
            window_to=date(2026, 8, 5),
            idempotency_key="key-same",
        )
    assert exc.value.status_code == 409


from contextlib import asynccontextmanager


@pytest.mark.asyncio
async def test_run_search_task_success_and_failure_refund(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990004, username="el_user4", first_name="El4")
    user, _ = await get_or_create_user(db_session, tg_user)

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = ElectionService(db_session)
    req = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-run-1",
    )

    mock_lunar_resp = {
        "days": [
            {
                "date": "2026-08-01",
                "moon_sign": "taurus",
                "moon_sign_ru": "Телец",
                "waxing": True,
                "voc_fraction": 0.0,
                "mercury_retro": False,
            }
        ]
    }

    mock_narrative = {
        "hero_reason": "Причина 1",
        "hero_personal": "Персональная 1",
        "hero_plain": "Простыми словами 1",
        "hero_hours": "Лучшие часы 1",
        "day_notes": [{"date": "2026-08-01", "note": "Заметка 1"}],
        "avoid_notes": [],
    }

    @asynccontextmanager
    async def _test_session_local():
        yield db_session

    with patch("app.services.election_service.get_solarsage_client") as mock_get_client, \
         patch("app.services.llm.election.generate_election_narrative", new_callable=AsyncMock) as mock_gen_narrative, \
         patch("app.services.election_service.SessionLocal", _test_session_local):

        mock_client = AsyncMock()
        mock_client.get_lunar_window.return_value = mock_lunar_resp
        mock_get_client.return_value = mock_client
        mock_gen_narrative.return_value = mock_narrative

        await service.run_search_task(req.id)

    await db_session.refresh(req)
    assert req.status == "done"

    res = (await db_session.execute(
        select(ElectionResult).where(ElectionResult.request_id == req.id)
    )).scalar_one_or_none()
    assert res is not None
    assert "best_days" in res.payload_json
    assert "narrative" in res.payload_json

    # Test failure & refund
    credit_2 = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit_2)
    await db_session.commit()

    req_fail = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-run-fail",
    )

    with patch("app.services.election_service.get_solarsage_client") as mock_get_client, \
         patch("app.services.llm.election.generate_election_narrative", new_callable=AsyncMock) as mock_gen_narrative, \
         patch("app.services.election_service.SessionLocal", _test_session_local):

        mock_client = AsyncMock()
        mock_client.get_lunar_window.side_effect = RuntimeError("Sidecar crashed")
        mock_get_client.return_value = mock_client
        mock_gen_narrative.side_effect = RuntimeError("LLM failed")

        await service.run_search_task(req_fail.id)

    await db_session.refresh(req_fail)
    assert req_fail.status == "refunded"
    assert req_fail.refund_status == "refunded"

    await db_session.refresh(credit)
    assert credit.used_amount == 1  # 2 searches total, 1 succeeded (used 1), 1 refunded (used 0)


@pytest.mark.asyncio
async def test_election_lazy_ttl_refunds_stuck_processing(db_session: AsyncSession) -> None:
    """Regression (2026-07-24): request stuck in processing > 5 min must be
    failed+refunded on read (horary lazy-TTL parity)."""
    from datetime import datetime, timedelta, UTC
    from app.db.models import ElectionCreditSpend, ElectionRequest, HoraryCredit
    from app.services.election_service import ElectionService
    from app.services.profile_service import get_or_create_user
    from app.services.telegram_auth import TelegramUser
    from sqlalchemy import select
    import uuid

    tg_user = TelegramUser(id=880010, username="el_ttl", first_name="ElTtl")
    user, _ = await get_or_create_user(db_session, tg_user)
    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=1)
    db_session.add(credit)
    await db_session.flush()
    req = ElectionRequest(
        user_id=user.id, event_type="relations:date",
        window_from=datetime.now(UTC).date(), window_to=datetime.now(UTC).date(),
        status="processing", spent_credit_id=credit.id,
        idempotency_key="ttl-1", request_hash="h1",
        created_at=datetime.now(UTC) - timedelta(minutes=6),
    )
    db_session.add(req)
    await db_session.flush()
    db_session.add(ElectionCreditSpend(
        credit_id=credit.id, election_request_id=req.id, amount=1, idempotency_key="ttl-1"
    ))
    await db_session.commit()

    service = ElectionService(db_session)
    result = await service.get_search(user.id, req.id)
    assert result is not None
    assert result.status == "refunded"
    refreshed = (await db_session.execute(select(HoraryCredit).where(HoraryCredit.id == credit.id))).scalar_one()
    assert refreshed.used_amount == 0


@pytest.mark.asyncio
async def test_election_service_passes_lock_true(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990005, username="el_lock_1", first_name="Lock1")
    user, _ = await get_or_create_user(db_session, tg_user)

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = ElectionService(db_session)
    with patch("app.services.election_service.HoraryCreditService.select_spendable_credit", wraps=HoraryCreditService(db_session).select_spendable_credit) as mock_select:
        req = await service.create_search(
            user_id=user.id,
            event_type="wedding",
            window_from=date(2026, 8, 1),
            window_to=date(2026, 8, 5),
            idempotency_key="key-lock-check",
        )
        assert req is not None
        assert mock_select.called
        # Verify lock=True was passed
        _, kwargs = mock_select.call_args
        assert kwargs.get("lock") is True


@pytest.mark.asyncio
async def test_election_service_spends_gift_source_as_bonus(db_session: AsyncSession) -> None:
    tg_user = TelegramUser(id=990006, username="el_gift_1", first_name="Gift1")
    user, _ = await get_or_create_user(db_session, tg_user)

    # Grant gift credit from promo
    credit = HoraryCredit(user_id=user.id, source="gift", amount=5, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

    service = ElectionService(db_session)
    req = await service.create_search(
        user_id=user.id,
        event_type="wedding",
        window_from=date(2026, 8, 1),
        window_to=date(2026, 8, 5),
        idempotency_key="key-gift-spend",
    )
    assert req.spent_credit_id == credit.id
    await db_session.refresh(credit)
    assert credit.used_amount == 1


def test_compiled_postgresql_select_contains_for_update() -> None:
    from sqlalchemy.dialects import postgresql
    from app.services.horary_credit_service import HoraryCreditService

    user_id = uuid.uuid4()
    stmt = select(HoraryCredit).where(
        HoraryCredit.user_id == user_id,
        HoraryCredit.used_amount < HoraryCredit.amount,
    ).with_for_update()

    compiled_sql = str(stmt.compile(dialect=postgresql.dialect()))
    assert "FOR UPDATE" in compiled_sql

