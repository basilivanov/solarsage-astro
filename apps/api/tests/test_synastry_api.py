"""Unit tests for synastry API routes and security."""

from unittest.mock import AsyncMock, patch
import uuid
import pytest

from fastapi import HTTPException, status
from app.api.synastry import router
from app.schemas.synastry import AspectDrilldown, PartnerCreate, SynastryAspect


def test_synastry_aspect_schemas_accept_engine_tones():
    """Scoring engine tone vocabulary (03_SCORING_AND_TONE_CONTRACT) must pass response validation."""
    for tone in ("supportive", "mixed", "tense", "good", "mid", "bad"):
        aspect = SynastryAspect(id="sun_trine_moon", title="Солнце трин Луна", tone=tone)
        assert aspect.tone == tone
        drilldown = AspectDrilldown(aspectId="sun_trine_moon", title="t", tone=tone, explanation="e")
        assert drilldown.tone == tone


def test_synastry_router_import():
    assert router is not None
    assert router.prefix == "/api/synastry"


def test_synastry_static_routes_ordering():
    # Verify static routes (/capabilities, /quota) are registered before dynamic routes (/{partner_id})
    paths = [route.path for route in router.routes]
    cap_index = paths.index("/api/synastry/capabilities")
    quota_index = paths.index("/api/synastry/quota")
    dynamic_index = paths.index("/api/synastry/{partner_id}")

    assert cap_index < dynamic_index
    assert quota_index < dynamic_index


def test_synastry_route_definitions():
    # Verify exact required routes exist
    route_map = {(r.path, tuple(r.methods)): r for r in router.routes}
    
    assert ("/api/synastry/capabilities", ("GET",)) in route_map
    assert ("/api/synastry/quota", ("GET",)) in route_map
    assert ("/api/synastry", ("GET",)) in route_map
    assert ("/api/synastry/partners", ("POST",)) in route_map
    assert ("/api/synastry/{partner_id}", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/status", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/aspect/{aspect_id}", ("GET",)) in route_map
    assert ("/api/synastry/{partner_id}/feedback", ("POST",)) in route_map
    assert ("/api/synastry/{partner_id}", ("DELETE",)) in route_map


@pytest.mark.asyncio
async def test_create_partner_endpoint_202_and_task_trigger():
    """POST /api/synastry/partners returns 202 Accepted and triggers background calculation task."""
    from app.api.synastry import create_synastry_partner
    from app.db.models import SynastryPartner, SynastryReport

    user_id = uuid.uuid4()
    partner_id = uuid.uuid4()
    report_id = uuid.uuid4()

    dummy_user = AsyncMock()
    dummy_user.id = user_id
    dummy_db = AsyncMock()

    dummy_partner = SynastryPartner(id=partner_id, owner_id=user_id, name="Максим")
    dummy_report = SynastryReport(id=report_id, owner_id=user_id, partner_id=partner_id, state="pending", stage="init", attempt_count=0)

    body = PartnerCreate(
        name="Максим",
        relation="romantic",
        birth_date="1987-09-09", # type: ignore[arg-type]
    )

    with patch("app.api.synastry.SynastryService") as mock_service_cls, \
         patch("app.api.synastry.asyncio.create_task") as mock_create_task:

        mock_instance = AsyncMock()
        mock_instance.create_partner_and_report.return_value = (dummy_partner, dummy_report, True)
        mock_service_cls.return_value = mock_instance

        res = await create_synastry_partner(body, dummy_user, dummy_db)

        assert res.report_id == report_id
        assert res.partner_id == partner_id
        assert res.state == "pending"
        mock_create_task.assert_called_once()

        # Clean up unawaited mocked coroutine
        coro = mock_create_task.call_args[0][0]
        coro.close()


def test_synastry_partner_item_schema_counters_and_report_state():
    """SynastryPartnerItem schema includes optional counters and report_state fields."""
    from datetime import date, datetime, timezone
    from app.schemas.synastry import SynastryPartnerItem

    item = SynastryPartnerItem(
        id=uuid.uuid4(),
        name="Максим",
        relation_type="romantic",
        birth_date=date(1987, 9, 9),
        precision="exact",
        score=89,
        status="good",
        summary="Отличная совместимость",
        counters={"good": 8, "mid": 2, "bad": 2},
        report_state="ready",
        created_at=datetime.now(timezone.utc),
    )

    dumped = item.model_dump(by_alias=True)
    assert dumped["counters"] == {"good": 8, "mid": 2, "bad": 2}
    assert dumped["reportState"] == "ready"


@pytest.mark.asyncio
async def test_synastry_capabilities_and_quota_shared_balance():
    """Capabilities and quota routes use HoraryCreditService.get_balance and return consistent fields."""
    from app.api.synastry import get_synastry_capabilities, get_synastry_quota
    from app.schemas.horary import HoraryQuotaRead

    user_id = uuid.uuid4()
    dummy_user = AsyncMock()
    dummy_user.id = user_id
    dummy_db = AsyncMock()

    mock_quota = HoraryQuotaRead(
        weeklyFreeAvailable=True,
        weeklyFreeExpiresAt="2026-08-01T00:00:00Z",
        nextWeeklyFreeAt=None,
        bonusCredits=2,
        paidCredits=1,
        canPurchase=True,
    )

    dummy_db.execute.return_value = AsyncMock(scalars=lambda: AsyncMock(all=lambda: []))

    with patch("app.api.synastry.HoraryCreditService") as mock_svc_cls:
        mock_svc = AsyncMock()
        mock_svc.get_balance.return_value = mock_quota
        mock_svc_cls.return_value = mock_svc

        caps = await get_synastry_capabilities(dummy_user, dummy_db)
        quota = await get_synastry_quota(dummy_user, dummy_db)

        # 1 + 2 + 1 = 4
        assert caps.credit_balance == 4
        assert caps.can_calculate is True
        assert caps.can_purchase is True
        assert caps.blocked_reason is None

        assert quota.weekly_free_available is True
        assert quota.bonus_credits == 2
        assert quota.paid_credits == 1
