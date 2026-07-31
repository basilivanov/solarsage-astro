from __future__ import annotations

from datetime import date, datetime, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import EveningCheckin, UserProfile
import app.services.checkin_service as checkin_service_module


async def _login(
    async_client: AsyncClient,
    make_initdata,
    *,
    user_id: int,
    username: str,
) -> None:
    user_raw = make_initdata(user_id=user_id, username=username)
    response = await async_client.post(
        "/api/auth/telegram",
        json={"initData": user_raw},
    )
    assert response.status_code == 200


async def _set_profile_timezone(db_session: AsyncSession, tz: str) -> None:
    profile = (await db_session.execute(select(UserProfile))).scalar_one()
    profile.current_tz = tz
    await db_session.commit()


@pytest.mark.asyncio
async def test_post_checkin_accepts_numeric_payload_and_returns_real_contract(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223001,
        username="checkin_contract",
    )

    response = await async_client.post(
        "/api/checkin",
        json={
            "targetDate": "2026-07-06",
            "mood": 5,
            "accuracy": 3,
            "energy": 4,
            "tags": ["work_win", "calm"],
            "note": "Matched the calmer afternoon.",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data == {
        "id": data["id"],
        "targetDate": "2026-07-06",
        "mood": 5,
        "accuracy": 3,
        "energy": 4,
        "tags": ["work_win", "calm"],
        "note": "Matched the calmer afternoon.",
        "streak": 1,
        "filledAt": data["filledAt"],
        "createdAt": data["createdAt"],
        "observedSpheres": None,
        "forecastSnapshotId": None,
        "predictionSeenAt": None,
        "predictionSeenSurface": None,
    }
    filled_at = datetime.fromisoformat(data["filledAt"].replace("Z", "+00:00"))
    assert filled_at.utcoffset() == timezone.utc.utcoffset(filled_at)


@pytest.mark.asyncio
async def test_post_checkin_upserts_same_user_and_target_date(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223002,
        username="checkin_upsert",
    )

    first = await async_client.post(
        "/api/checkin",
        json={
            "targetDate": "2026-07-06",
            "mood": 2,
            "accuracy": 1,
            "energy": 2,
            "tags": ["tired"],
            "note": "First pass",
        },
    )
    second = await async_client.post(
        "/api/checkin",
        json={
            "targetDate": "2026-07-06",
            "mood": 4,
            "accuracy": 2,
            "energy": 5,
            "tags": ["support"],
            "note": "Updated after reflection",
        },
    )

    assert first.status_code == 200
    assert second.status_code == 200
    first_data = first.json()
    second_data = second.json()
    assert second_data["id"] == first_data["id"]
    assert second_data["mood"] == 4
    assert second_data["accuracy"] == 2
    assert second_data["energy"] == 5
    assert second_data["tags"] == ["support"]
    assert second_data["note"] == "Updated after reflection"


@pytest.mark.asyncio
async def test_get_checkin_by_target_date_reads_numeric_contract(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223003,
        username="checkin_get",
    )
    await async_client.post(
        "/api/checkin",
        json={
            "targetDate": "2026-07-05",
            "mood": 3,
            "accuracy": 2,
            "energy": 3,
            "tags": [],
            "note": None,
        },
    )

    response = await async_client.get("/api/checkin/2026-07-05")

    assert response.status_code == 200
    data = response.json()
    assert data["targetDate"] == "2026-07-05"
    assert data["mood"] == 3
    assert data["accuracy"] == 2
    assert data["energy"] == 3
    assert data["tags"] == []
    assert data["note"] is None


@pytest.mark.asyncio
async def test_get_checkin_returns_null_wrapper_when_missing(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223004,
        username="checkin_missing",
    )

    response = await async_client.get("/api/checkin/2026-07-05")

    assert response.status_code == 200
    assert response.json() == {"checkin": None}


@pytest.mark.asyncio
async def test_yesterday_uses_profile_timezone_not_utc_date(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
    monkeypatch: pytest.MonkeyPatch,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223005,
        username="checkin_tz",
    )
    await _set_profile_timezone(db_session, "America/Los_Angeles")
    monkeypatch.setattr(
        checkin_service_module,
        "utc_now",
        lambda: datetime(2026, 1, 2, 1, 30, tzinfo=timezone.utc),
        raising=False,
    )
    await async_client.post(
        "/api/checkin",
        json={
            "targetDate": "2025-12-31",
            "mood": 4,
            "accuracy": 3,
            "energy": 4,
            "tags": ["calm"],
            "note": "Local yesterday in Los Angeles",
        },
    )

    response = await async_client.get("/api/checkin/yesterday")

    assert response.status_code == 200
    data = response.json()
    assert data["hadCheckin"] is True
    assert data["checkin"]["targetDate"] == "2025-12-31"
    assert data["checkin"]["mood"] == 4


@pytest.mark.asyncio
async def test_metrics_returns_real_aggregates_and_streaks(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223006,
        username="checkin_metrics",
    )
    payloads = [
        ("2026-07-01", 3, 1, 2, ["tired"]),
        ("2026-07-02", 4, 2, 3, ["support", "calm"]),
        ("2026-07-04", 5, 3, 5, ["support"]),
    ]
    for target_date, mood, accuracy, energy, tags in payloads:
        response = await async_client.post(
            "/api/checkin",
            json={
                "targetDate": target_date,
                "mood": mood,
                "accuracy": accuracy,
                "energy": energy,
                "tags": tags,
                "note": None,
            },
        )
        assert response.status_code == 200

    response = await async_client.get(
        "/api/checkin/metrics?from=2026-07-01&to=2026-07-04",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["totalCheckins"] == 3
    assert data["currentStreak"] == 1
    assert data["longestStreak"] == 2
    assert data["averageMood"] == pytest.approx(4.0)
    assert data["averageEnergy"] == pytest.approx(10 / 3)
    assert data["averageAccuracy"] == pytest.approx(2.0)
    assert data["moodDistribution"] == {"3": 1, "4": 1, "5": 1}
    assert data["accuracyDistribution"] == {"1": 1, "2": 1, "3": 1}
    assert data["tagFrequency"] == {"tired": 1, "support": 2, "calm": 1}


@pytest.mark.asyncio
async def test_metrics_current_streak_is_zero_when_latest_checkin_is_before_to_date(
    async_client: AsyncClient,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223008,
        username="checkin_stale_streak",
    )
    for target_date in ("2026-07-01", "2026-07-02"):
        response = await async_client.post(
            "/api/checkin",
            json={
                "targetDate": target_date,
                "mood": 4,
                "accuracy": 2,
                "energy": 3,
                "tags": [],
                "note": None,
            },
        )
        assert response.status_code == 200

    response = await async_client.get(
        "/api/checkin/metrics?from=2026-07-01&to=2026-07-06",
    )

    assert response.status_code == 200
    data = response.json()
    assert data["totalCheckins"] == 2
    assert data["longestStreak"] == 2
    assert data["currentStreak"] == 0


@pytest.mark.asyncio
async def test_legacy_string_mood_and_notes_remain_readable(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
):
    await _login(
        async_client,
        make_initdata,
        user_id=223007,
        username="checkin_legacy",
    )
    profile = (await db_session.execute(select(UserProfile))).scalar_one()
    db_session.add(
        EveningCheckin(
            user_id=profile.user_id,
            target_date=date(2026, 7, 3),
            mood="great",
            notes="Legacy notes column",
        ),
    )
    await db_session.commit()

    response = await async_client.get("/api/checkin/2026-07-03")

    assert response.status_code == 200
    data = response.json()
    assert data["mood"] == 5
    assert data["note"] == "Legacy notes column"
