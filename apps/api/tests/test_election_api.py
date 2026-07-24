# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_ELECTION_API
# ROLE: API tests for /api/election endpoints
# DEPENDENCIES: pytest, httpx, app.main
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-ELECTION-API
# purpose: Test /api/election/quota, /api/election/searches endpoints.
# owns:
#   - apps/api/tests/test_election_api.py
# inputs: async_client, make_initdata
# outputs: pytest assertions
# END_MODULE_CONTRACT: M-TEST-ELECTION-API

from datetime import date
from unittest.mock import AsyncMock, patch
import pytest
from httpx import AsyncClient

from app.db.models import HoraryCredit
from app.services.profile_service import get_or_create_user
from app.services.telegram_auth import TelegramUser


@pytest.mark.asyncio
async def test_election_quota_endpoint(async_client: AsyncClient, make_initdata, db_session) -> None:
    raw_init = make_initdata(user_id=880001, username="el_api_1")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    resp = await async_client.get("/api/election/quota")
    assert resp.status_code == 200
    data = resp.json()
    assert "paidCredits" in data
    assert "canPurchase" in data


@pytest.mark.asyncio
async def test_election_searches_flow(async_client: AsyncClient, make_initdata, db_session) -> None:
    raw_init = make_initdata(user_id=880002, username="el_api_2")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    # Find user and add credit
    tg_user = TelegramUser(id=880002, username="el_api_2", first_name="ElApi2")
    user, _ = await get_or_create_user(db_session, tg_user)

    credit = HoraryCredit(user_id=user.id, source="paid", amount=1, used_amount=0)
    db_session.add(credit)
    await db_session.commit()

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

    with patch("app.services.election_service.get_solarsage_client") as mock_get_client, \
         patch("app.services.llm.election.generate_election_narrative", new_callable=AsyncMock) as mock_gen_narrative:

        mock_client = AsyncMock()
        mock_client.get_lunar_window.return_value = mock_lunar_resp
        mock_get_client.return_value = mock_client
        mock_gen_narrative.return_value = mock_narrative

        # POST /api/election/searches
        post_resp = await async_client.post(
            "/api/election/searches",
            json={
                "eventType": "wedding",
                "windowFrom": "2026-08-01",
                "windowTo": "2026-08-05",
                "idempotencyKey": "key-api-1",
            },
        )
        assert post_resp.status_code == 201
        search_data = post_resp.json()
        assert search_data["eventType"] == "wedding"
        search_id = search_data["id"]

        import asyncio
        await asyncio.sleep(0.1)

        # GET /api/election/searches
        list_resp = await async_client.get("/api/election/searches")
        assert list_resp.status_code == 200
        list_data = list_resp.json()
        assert len(list_data) == 1
        assert list_data[0]["id"] == search_id

        # GET /api/election/searches/{id}
        get_resp = await async_client.get(f"/api/election/searches/{search_id}")
        assert get_resp.status_code == 200
        assert get_resp.json()["id"] == search_id

        # GET foreign / unknown search -> 404
        fake_id = "00000000-0000-0000-0000-000000000000"
        unknown_resp = await async_client.get(f"/api/election/searches/{fake_id}")
        assert unknown_resp.status_code == 404


@pytest.mark.asyncio
async def test_election_quota_persists_weekly_credit_for_fresh_user(
    async_client: AsyncClient, make_initdata, db_session
) -> None:
    """Regression (2026-07-24): quota GET must COMMIT the lazily-created weekly
    credit — without the commit the row rolled back and the following search
    402'd for fresh users even though quota showed weeklyFreeAvailable=true."""
    from datetime import date as Date, timedelta
    from app.db.models import AccessLedger, HoraryCredit
    from sqlalchemy import select

    raw_init = make_initdata(user_id=880003, username="el_api_3")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})

    tg_user = TelegramUser(id=880003, username="el_api_3", first_name="ElApi3")
    user, _ = await get_or_create_user(db_session, tg_user)
    db_session.add(AccessLedger(
        user_id=user.id, entry_type="subscription", days_granted=30,
        start_date=Date.today(), end_date=Date.today() + timedelta(days=29),
    ))
    await db_session.commit()

    resp = await async_client.get("/api/election/quota")
    assert resp.status_code == 200
    assert resp.json()["weeklyFreeAvailable"] is True

    row = (await db_session.execute(
        select(HoraryCredit).where(HoraryCredit.user_id == user.id)
    )).scalar_one_or_none()
    assert row is not None, "weekly credit must be persisted by the quota GET"
    assert row.source == "subscription_weekly_free"
