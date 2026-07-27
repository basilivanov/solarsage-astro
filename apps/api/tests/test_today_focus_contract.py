# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_FOCUS_CONTRACT
# ROLE: Contract and integration tests for TodayFocus API block (Slice C1).
# DEPENDENCIES: pytest, app.schemas.today_focus, app.schemas.today, app.services.today_service
# ############################################################################

from datetime import date, datetime, timezone
import pytest

from app.schemas.today import TodayPayload
from app.schemas.today_focus import (
    TodayFocus,
    TodayConvergence,
    TodayFocusEvent,
    TodayFeaturedSphere,
)
from app.services.today_focus_builder import TodayFactor, build_today_focus


def test_today_focus_schema_invariants():
    """Contract §5: state != convergence_today requires convergence=None and featured_spheres=[]."""
    # 1. single_impulses state
    tf_single = TodayFocus(
        state="single_impulses",
        convergence=None,
        events=[
            TodayFocusEvent(
                id="ev:1",
                kind="exact",
                occurs_at=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
                local_date=date(2026, 7, 28),
                timezone="Europe/Moscow",
                precision="minute",
                human_title="Марс напротив твоей Луны",
                technical_title="Марс оппозиция Луна",
                meaning=None,
                source_activation_ids=["act-1"],
            )
        ],
        featured_spheres=[],
        content_state="not_needed",
    )
    assert tf_single.state == "single_impulses"
    assert tf_single.convergence is None
    assert tf_single.featured_spheres == []

    # 2. convergence_today state
    tf_conv = TodayFocus(
        state="convergence_today",
        convergence=TodayConvergence(
            id="conv:1",
            theme_key="NEPTUNE",
            title="Что сошлось именно сегодня",
            summary=None,
            independent_factor_count=2,
            technique_families=["transit"],
            source_activation_ids=["act-1", "act-2"],
        ),
        events=[
            TodayFocusEvent(
                id="ev:1",
                kind="exact",
                occurs_at=datetime(2026, 7, 28, 12, 0, 0, tzinfo=timezone.utc),
                local_date=date(2026, 7, 28),
                timezone="Europe/Moscow",
                precision="minute",
                human_title="Марс напротив твоей Луны",
                technical_title="Марс оппозиция Луна",
                meaning=None,
                source_activation_ids=["act-1"],
            )
        ],
        featured_spheres=[
            TodayFeaturedSphere(
                key="work",
                relevance_rank=1,
                state="convergence_today",
                summary=None,
                action=None,
                convergence_id="conv:1",
                source_event_ids=["ev:1"],
                source_activation_ids=["act-1"],
            )
        ],
        content_state="not_needed",
    )
    assert tf_conv.state == "convergence_today"
    assert tf_conv.convergence is not None
    assert len(tf_conv.featured_spheres) == 1


def test_today_focus_events_sorting_and_tz():
    """Contract §5: events are sorted by occurs_at + id and occurs_at has timezone."""
    dt1 = datetime(2026, 7, 28, 10, 30, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 7, 28, 16, 52, 0, tzinfo=timezone.utc)

    f1 = TodayFactor(
        factor_id="sig:aspect:MOON:OPPOSITION:NEPTUNE",
        activation_ids=("act-2",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MOON",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("relationships",),
        polarity="tense",
        strength=0.75,
        salience=0.75,
        active_from=None,
        exact_at=dt1,
        active_until=None,
        phase="exact",
        temporal_role="anchor_today",
    )
    f2 = TodayFactor(
        factor_id="sig:aspect:MARS:OPPOSITION:NEPTUNE",
        activation_ids=("act-1",),
        technique="transit_to_natal",
        technique_family="transit",
        source_key="MARS",
        target_key="NEPTUNE",
        theme_keys=("action",),
        product_spheres=("work",),
        polarity="tense",
        strength=0.85,
        salience=0.85,
        active_from=None,
        exact_at=dt2,
        active_until=None,
        phase="exact",
        temporal_role="anchor_today",
    )

    res = build_today_focus([f1, f2], tz_name="Europe/Moscow", target_date=date(2026, 7, 28))
    assert res.state == "convergence_today"
    assert len(res.events) == 2
    # Events sorted by occurs_at (dt1 < dt2)
    assert res.events[0].occurs_at == dt1
    assert res.events[1].occurs_at == dt2
    assert res.events[0].occurs_at.tzinfo is not None


@pytest.mark.asyncio
async def test_today_service_builds_focus_in_payload(async_client, make_initdata, db_session):
    """Integration: GET /api/day/today returns a valid TodayPayload with non-null focus block."""
    from datetime import timedelta, date as Date
    from sqlalchemy import select
    from app.db.models import AccessLedger, User

    raw_init = make_initdata(user_id=987654, username="focus_user")
    await async_client.post("/api/auth/telegram", json={"initData": raw_init})
    await async_client.put(
        "/api/profile",
        json={
            "gender": "male",
            "birth": {
                "birthday": "1990-01-15",
                "birthTime": "12:00",
                "birthCity": "Moscow",
                "birthLat": 55.75,
                "birthLon": 37.61,
                "birthTz": "Europe/Moscow",
            },
        },
    )

    user = (await db_session.execute(select(User).where(User.tg_user_id == 987654))).scalar_one()
    db_session.add(AccessLedger(
        user_id=user.id, entry_type="subscription", days_granted=30,
        start_date=Date.today() - timedelta(days=1), end_date=Date.today() + timedelta(days=29),
    ))
    await db_session.commit()

    resp = await async_client.get("/api/day/2026-07-28")
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "focus" in data
    focus = data["focus"]
    assert focus is not None
    assert focus["state"] in ("convergence_today", "single_impulses", "background_only", "no_accent")
    assert focus["contentState"] == "not_needed"
    assert isinstance(focus["events"], list)
    assert isinstance(focus["featuredSpheres"], list)
