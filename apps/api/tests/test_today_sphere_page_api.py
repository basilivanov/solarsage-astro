# ############################################################################
# AI_HEADER: TEST_TODAY-SPHERE-PAGE-API — static sphere HTTP contract tests.
# ROLE: Proves authentication, profile/access gates, and the two-layer public
#   wire response for GET /api/spheres/{key}.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-PAGE-API
# purpose: Validate the authenticated static sphere page endpoint at the HTTP
#   boundary without real SolarSage or LLM calls.
# owns:
#   - apps/api/tests/test_today_sphere_page_api.py
# inputs: authenticated test sessions, onboarding profiles, and patched provider responses.
# outputs: assertions for stable errors, camelCase payload, and unavailable period state.
# dependencies: FastAPI route, conftest async client/database fixtures.
# side_effects: isolated SQLite rows only; external providers are mocked.
# emitted_logs: none.
# invariants: locked access is rejected before provider work; natal failure is
#   represented by state=unavailable rather than template text.
# failure_policy: pytest assertions fail closed on access/privacy or wire drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-PAGE-API

# START_MODULE_MAP: M-TEST-TODAY-SPHERE-PAGE-API
# public_entrypoints:
#   - test_sphere_page_requires_authentication
#   - test_sphere_page_rejects_invalid_and_incomplete_requests
#   - test_sphere_page_returns_natal_and_period_layers
#   - test_sphere_page_accepts_all_canonical_keys
#   - test_sphere_page_keeps_natal_when_period_sidecar_is_unavailable
# semantic_blocks:
#   - AUTH_AND_PROFILE: session, canonical key, and onboarding checks.
#   - PAGE_WIRE: ready natal and deterministic period projection.
#   - PERIOD_FAILURE: honest sidecar-unavailable projection.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SPHERE-PAGE-API

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User, UserProfile
from app.schemas.natal import NatalChartPlanet, NatalContextData
from app.services.today_sphere_page_service import CANONICAL_SPHERES


async def _login(async_client: AsyncClient, make_initdata, user_id: int) -> None:
    response = await async_client.post(
        "/api/auth/telegram",
        json={"initData": make_initdata(user_id=user_id, username=f"sphere_{user_id}")},
    )
    assert response.status_code == 200


def _context() -> NatalContextData:
    return NatalContextData(
        planets=[
            NatalChartPlanet(
                name="SUN", sign="Leo", degree=10.0, house=10, retrograde=False, longitude=130.0
            )
        ],
        sphere_scores={"work": 0.75},
    )


async def _complete_profile(db_session: AsyncSession, tg_user_id: int, *, mode: str = "exact") -> User:
    user = (
        await db_session.execute(select(User).where(User.tg_user_id == tg_user_id))
    ).scalar_one()
    profile = (
        await db_session.execute(select(UserProfile).where(UserProfile.user_id == user.id))
    ).scalar_one_or_none()
    if profile is None:
        profile = UserProfile(user_id=user.id)
        db_session.add(profile)
    profile.birthday = date(1990, 1, 2)
    profile.birth_time = time(14, 30)
    profile.birth_time_mode = mode
    profile.birth_lat = 55.75
    profile.birth_lon = 37.62
    profile.birth_tz = "Europe/Moscow"
    profile.gender = "female"
    profile.is_onboarded = True
    await db_session.commit()
    return user


class _PeriodClient:
    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls = 0

    async def get_activation_layer(self, **kwargs):
        self.calls += 1
        if self.fail:
            raise TimeoutError("sidecar timeout")
        return {
            "activations": [
                {
                    "technique": "firdar_major",
                    "target_type": "planet",
                    "target_key": "SUN",
                    "active_from": "2024-05-01",
                    "active_until": "2031-05-01",
                }
            ]
        }


class _NatalLLM:
    async def generate(self, prompt: str, *, max_output_tokens: int, timeout_seconds: float):
        return {
            "paragraphs": [
                {
                    "text": "Солнце в карте подчёркивает заметную роль в работе.",
                    "sourceFactIds": ["natal:planet:SUN"],
                }
            ]
        }


# START_BLOCK: AUTH_AND_PROFILE
@pytest.mark.asyncio
async def test_sphere_page_requires_authentication(async_client: AsyncClient) -> None:
    response = await async_client.get("/api/spheres/work")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_sphere_page_rejects_invalid_and_incomplete_requests(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 247001)
    for invalid_key in ("not-a-sphere", "money", "decisions", "shopping"):
        invalid = await async_client.get(f"/api/spheres/{invalid_key}")
        assert invalid.status_code == 422
        assert invalid.json() == {"detail": {"code": "INVALID_SPHERE"}}

    incomplete = await async_client.get("/api/spheres/work")
    assert incomplete.status_code == 422
    assert incomplete.json()["detail"]["code"] == "NOT_ONBOARDED"
# END_BLOCK: AUTH_AND_PROFILE


# START_BLOCK: PAGE_WIRE
@pytest.mark.asyncio
async def test_sphere_page_returns_natal_and_period_layers(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 247002)
    user = await _complete_profile(db_session, 247002)
    client = _PeriodClient()
    from app.schemas.access import ContentAccessState

    with (
        patch("app.services.today_sphere_page_service.get_solarsage_client", return_value=client),
        patch(
            "app.services.today_sphere_page_service.AccessService.can_access_day",
            new=AsyncMock(
                return_value=ContentAccessState(
                    state="full",
                    reason="active_subscription",
                    referral_days_left=None,
                    subscription_active=True,
                    access_until="2027-01-01",
                )
            ),
        ),
        patch(
            "app.services.today_sphere_page_service.NatalContextService.get_or_build_natal_context",
            new=AsyncMock(return_value=_context()),
        ),
        patch("app.services.llm_service.LLMService", return_value=_NatalLLM()),
    ):
        response = await async_client.get("/api/spheres/work")

    assert response.status_code == 200
    data = response.json()
    assert data["sphere"] == "work"
    assert data["birthTimeMode"] == "exact"
    assert data["housesAvailable"] is True
    assert data["natal"]["state"] == "ready"
    assert data["natal"]["paragraphs"][0]["sourceFactIds"] == ["natal:planet:SUN"]
    assert data["period"][0]["title"] == "Большой фирдар Солнца"
    assert data["period"][0]["note"]
    assert data["periodSynthesis"]
    assert data["periodUnavailable"] is False
    assert len(data["periodIdentity"]) == 32
    assert client.calls == 1
    assert user.id


@pytest.mark.asyncio
async def test_sphere_page_accepts_all_canonical_keys(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 247005)
    await _complete_profile(db_session, 247005)
    from app.schemas.access import ContentAccessState

    with (
        patch("app.services.today_sphere_page_service.get_solarsage_client", return_value=_PeriodClient()),
        patch(
            "app.services.today_sphere_page_service.AccessService.can_access_day",
            new=AsyncMock(
                return_value=ContentAccessState(
                    state="full",
                    reason="active_subscription",
                    referral_days_left=None,
                    subscription_active=True,
                    access_until="2027-01-01",
                )
            ),
        ),
        patch(
            "app.services.today_sphere_page_service.NatalContextService.get_or_build_natal_context",
            new=AsyncMock(return_value=_context()),
        ),
        patch("app.services.llm_service.LLMService", return_value=_NatalLLM()),
    ):
        for sphere_key in sorted(CANONICAL_SPHERES):
            response = await async_client.get(f"/api/spheres/{sphere_key}")
            assert response.status_code == 200
            assert response.json()["sphere"] == sphere_key


@pytest.mark.asyncio
async def test_sphere_page_keeps_natal_when_period_sidecar_is_unavailable(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 247003)
    await _complete_profile(db_session, 247003, mode="bucket")
    client = _PeriodClient(fail=True)
    from app.schemas.access import ContentAccessState

    with (
        patch("app.services.today_sphere_page_service.get_solarsage_client", return_value=client),
        patch(
            "app.services.today_sphere_page_service.AccessService.can_access_day",
            new=AsyncMock(
                return_value=ContentAccessState(
                    state="full",
                    reason="active_subscription",
                    referral_days_left=None,
                    subscription_active=True,
                    access_until="2027-01-01",
                )
            ),
        ),
        patch(
            "app.services.today_sphere_page_service.NatalContextService.get_or_build_natal_context",
            new=AsyncMock(return_value=_context()),
        ),
        patch("app.services.llm_service.LLMService", return_value=_NatalLLM()),
    ):
        response = await async_client.get("/api/spheres/work")

    assert response.status_code == 200
    data = response.json()
    assert data["period"] == []
    assert data["periodIdentity"] == ""
    assert data["periodSynthesis"] is None
    assert data["periodUnavailable"] is True
    assert data["natal"]["state"] == "ready"
    assert data["housesAvailable"] is False
    assert data["birthTimeMode"] == "bucket"
# END_BLOCK: PAGE_WIRE


# START_BLOCK: PERIOD_FAILURE
@pytest.mark.asyncio
async def test_sphere_page_locked_access_fails_before_provider_calls(
    async_client: AsyncClient,
    db_session: AsyncSession,
    make_initdata,
) -> None:
    await _login(async_client, make_initdata, 247004)
    await _complete_profile(db_session, 247004)
    from app.schemas.access import ContentAccessState

    with patch(
        "app.services.today_sphere_page_service.AccessService.can_access_day",
        new=AsyncMock(
            return_value=ContentAccessState(
                state="locked",
                reason="outside_access_window",
                referral_days_left=None,
                subscription_active=None,
                access_until=None,
            )
        ),
    ):
        response = await async_client.get("/api/spheres/work")

    assert response.status_code == 403
    assert response.json() == {"detail": {"code": "ACCESS_REQUIRED"}}
# END_BLOCK: PERIOD_FAILURE
