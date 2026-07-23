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

from datetime import date
from unittest.mock import AsyncMock, patch
import pytest
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import HoraryCredit, ElectionRequest, ElectionResult, ElectionCreditSpend
from app.services.election_service import ElectionService
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

    with patch("app.services.election_service.get_solarsage_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_lunar_window.return_value = mock_lunar_resp
        mock_get_client.return_value = mock_client

        await service.run_search_task(req.id)

    await db_session.refresh(req)
    assert req.status == "done"

    res = (await db_session.execute(
        select(ElectionResult).where(ElectionResult.request_id == req.id)
    )).scalar_one_or_none()
    assert res is not None
    assert "best_days" in res.payload_json

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

    with patch("app.services.election_service.get_solarsage_client") as mock_get_client:
        mock_client = AsyncMock()
        mock_client.get_lunar_window.side_effect = RuntimeError("Sidecar crashed")
        mock_get_client.return_value = mock_client

        await service.run_search_task(req_fail.id)

    await db_session.refresh(req_fail)
    assert req_fail.status == "refunded"
    assert req_fail.refund_status == "refunded"

    await db_session.refresh(credit)
    assert credit.used_amount == 1  # 2 searches total, 1 succeeded (used 1), 1 refunded (used 0)
