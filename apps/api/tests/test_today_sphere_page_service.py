# ############################################################################
# AI_HEADER: TEST_TODAY-SPHERE-PAGE-SERVICE — static sphere page service gates.
# ROLE: Exercises deterministic sphere filtering, sphere-scoped natal facts,
#   bounded narrative validation, and profile/prompt cache reuse.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-PAGE-SERVICE
# purpose: Validate the static sphere page service without network access.
# owns:
#   - apps/api/tests/test_today_sphere_page_service.py
# inputs: synthetic natal context, sidecar activation dictionaries, and an
#   isolated async database session.
# outputs: assertions for period identity, fact-pack capability boundaries,
#   narrative claim binding, and cache behavior.
# dependencies: TodaySpherePageService and conftest database fixtures.
# side_effects: isolated SQLite rows in the test database only.
# emitted_logs: none.
# invariants: no real LLM or SolarSage request is made; failure never creates a
#   null-content narrative cache row.
# failure_policy: pytest assertions fail closed on scope or cache drift.
# END_MODULE_CONTRACT: M-TEST-TODAY-SPHERE-PAGE-SERVICE

# START_MODULE_MAP: M-TEST-TODAY-SPHERE-PAGE-SERVICE
# public_entrypoints:
#   - test_fact_pack_is_sphere_scoped_and_honest_for_non_exact_time
#   - test_period_layer_filters_sorts_caps_and_uses_exact_techniques
#   - test_natal_generation_is_claim_bound_and_cached
#   - test_natal_failure_is_unavailable_without_null_cache_row
# semantic_blocks:
#   - FACT_PACK_GATES: deterministic natal projection and birth-time capability.
#   - PERIOD_GATES: sidecar technique/filter/title/date projection.
#   - NATAL_CACHE_GATES: one bounded call, validation, and cache identity.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SPHERE-PAGE-SERVICE

from __future__ import annotations

from datetime import date, time
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TodaySphereNatalNarrative, User, UserProfile
from app.schemas.natal import (
    NatalChartAspect,
    NatalChartHouse,
    NatalChartPlanet,
    NatalChartSpecialPoint,
    NatalContextData,
)
from app.services.natal_context_service import NatalContextService
from app.services.today_sphere_page_service import (
    TodaySpherePageService,
    _validate_natal_provider_response,
    build_sphere_natal_fact_pack,
)


def _context() -> NatalContextData:
    return NatalContextData(
        planets=[
            NatalChartPlanet(
                name="SUN", sign="Leo", degree=10.0, house=10, retrograde=False, longitude=130.0
            ),
            NatalChartPlanet(
                name="MARS", sign="Aries", degree=2.0, house=6, retrograde=False, longitude=2.0
            ),
            NatalChartPlanet(
                name="JUPITER", sign="Taurus", degree=4.0, house=2, retrograde=False, longitude=34.0
            ),
            NatalChartPlanet(
                name="MERCURY", sign="Virgo", degree=20.0, house=3, retrograde=False, longitude=170.0
            ),
        ],
        houses=[
            NatalChartHouse(number=3, sign="Virgo", degree=0.0, longitude=150.0),
            NatalChartHouse(number=6, sign="Sagittarius", degree=0.0, longitude=240.0),
            NatalChartHouse(number=10, sign="Aries", degree=0.0, longitude=0.0),
        ],
        aspects=[
            NatalChartAspect(
                planet_a="SUN", planet_b="MERCURY", aspect_type="trine", orb=1.2, applying=True
            ),
            NatalChartAspect(
                planet_a="VENUS", planet_b="MOON", aspect_type="square", orb=2.0, applying=False
            ),
        ],
        special_points=[
            NatalChartSpecialPoint(
                name="North Node", sign="Aries", degree=1.0, longitude=1.0, house=10
            )
        ],
        sphere_scores={"work": 0.82, "money": 0.11},
        dominants=["SUN", "NEPTUNE"],
    )


def _profile(*, mode: str = "exact", onboarded: bool = True) -> UserProfile:
    return UserProfile(
        user_id=uuid4(),
        birthday=date(1990, 1, 2),
        birth_time=time(14, 30),
        birth_time_mode=mode,
        birth_lat=55.75,
        birth_lon=37.62,
        birth_tz="Europe/Moscow",
        gender="female",
        is_onboarded=onboarded,
    )


def test_fact_pack_is_sphere_scoped_and_honest_for_non_exact_time() -> None:
    exact = build_sphere_natal_fact_pack(_context(), "work", "exact")
    exact_ids = {fact["id"] for fact in exact["facts"]}
    assert "natal:planet:SUN" in exact_ids
    assert "natal:planet:MARS" in exact_ids
    assert "natal:planet:JUPITER" in exact_ids
    assert "natal:house:10" in exact_ids
    assert "natal:house:6" in exact_ids
    assert "natal:score:work" in exact_ids
    assert "natal:aspect:MERCURY-SUN" in exact_ids
    assert "natal:planet:MERCURY" not in exact_ids
    assert exact["housesAvailable"] is True
    assert exact["availableSpecialPoints"] == ["NORTH NODE"]

    bucket = build_sphere_natal_fact_pack(_context(), "work", "bucket")
    bucket_ids = {fact["id"] for fact in bucket["facts"]}
    assert not any(value.startswith("natal:house:") for value in bucket_ids)
    assert bucket["housesAvailable"] is False
    assert bucket["availableSpecialPoints"] == []
    assert all("house" not in fact for fact in bucket["facts"] if fact["kind"] == "planet")


# START_BLOCK: PERIOD_GATES
@pytest.mark.asyncio
async def test_period_layer_filters_sorts_caps_and_uses_exact_techniques() -> None:
    profile = _profile()

    class FakeClient:
        def __init__(self) -> None:
            self.kwargs = None

        async def get_activation_layer(self, **kwargs):
            self.kwargs = kwargs
            return {
                "activations": [
                    {
                        "technique": "firdar_major",
                        "target_type": "planet",
                        "target_key": "JUPITER",
                        "active_from": "2024-05-01",
                        "active_until": "2031-05-01",
                    },
                    {
                        "technique": "annual_profection",
                        "target_type": "house",
                        "target_key": "10",
                        "house": 10,
                        "active_from": "2025-10-30",
                        "active_until": "2026-10-29",
                    },
                    {
                        "technique": "firdar_minor",
                        "target_type": "planet",
                        "target_key": "VENUS",
                        "active_from": "2024-01-01",
                        "active_until": "2024-02-01",
                    },
                    {
                        "technique": "solar_return",
                        "target_type": "planet",
                        "target_key": "SUN",
                        "house": 10,
                        "active_from": "2025-01-01",
                        "active_until": "2026-01-01",
                    },
                    {
                        "technique": "firdar_major",
                        "target_type": "planet",
                        "target_key": "UNKNOWN_POINT",
                        "active_from": "2020-01-01",
                        "active_until": "2020-02-01",
                    },
                ]
            }

    client = FakeClient()
    with patch("app.services.today_sphere_page_service.get_solarsage_client", return_value=client):
        service = TodaySpherePageService(object())
        items, unavailable = await service._build_period_layer(profile, date(2026, 7, 31), "work")

    assert unavailable is False
    assert client.kwargs["techniques"] == [
        "annual_profection",
        "firdar_major",
        "firdar_minor",
        "solar_return",
    ]
    assert [item.active_until for item in items] == sorted(item.active_until for item in items)
    assert len(items) == 3
    assert items[0].title == "Соляр: Солнце"
    assert items[1].title == "Год профекции: 10 дом"
    assert items[2].title == "Большой фирдар Юпитера"
    assert all(word not in item.title.casefold() for item in items for word in ("сегодня", "завтра"))
# END_BLOCK: PERIOD_GATES


def test_natal_special_point_validation_accepts_ru_alias_when_fact_is_available() -> None:
    content = _validate_natal_provider_response(
        {
            "paragraphs": [
                {
                    "text": "Хирон добавляет осторожность в работе.",
                    "sourceFactIds": ["natal:planet:SUN"],
                }
            ]
        },
        frozenset({"natal:planet:SUN"}),
        frozenset({"CHIRON"}),
    )

    assert content.paragraphs[0].source_fact_ids == ["natal:planet:SUN"]


@pytest.mark.parametrize(
    "text",
    [
        "Transit_Mars нельзя публиковать.",
        "Natal_Moon нельзя публиковать.",
        "Список M, Mars не является описанием.",
        "Natal, Planet, Moon — служебный вывод.",
    ],
)
def test_natal_provider_machine_driver_text_is_rejected(text: str) -> None:
    with pytest.raises(ValueError, match="schema_invalid"):
        _validate_natal_provider_response(
            {
                "paragraphs": [
                    {
                        "text": text,
                        "sourceFactIds": ["natal:planet:SUN"],
                    }
                ]
            },
            frozenset({"natal:planet:SUN"}),
            frozenset(),
        )


# START_BLOCK: NATAL_CACHE_GATES
@pytest.mark.asyncio
async def test_natal_generation_is_claim_bound_and_cached(db_session: AsyncSession) -> None:
    user = User(tg_user_id=uuid4().int % 2_000_000_000)
    profile = _profile()
    profile.user_id = user.id
    user.profile = profile
    db_session.add(user)
    await db_session.commit()

    class FakeLLM:
        def __init__(self) -> None:
            self.calls = 0
            self.prompts: list[str] = []

        async def generate(self, prompt: str, *, max_output_tokens: int, timeout_seconds: float):
            self.calls += 1
            self.prompts.append(prompt)
            assert max_output_tokens == 700
            assert timeout_seconds == 45.0
            return {
                "paragraphs": [
                    {
                        "text": "Солнце в карте поддерживает ясную роль в работе.",
                        "sourceFactIds": ["natal:planet:SUN"],
                    }
                ]
            }

    llm = FakeLLM()
    context_service = AsyncMock()
    context_service.return_value = _context()
    profile_hash = NatalContextService.compute_profile_hash(profile)
    with patch(
        "app.services.today_sphere_page_service.NatalContextService.get_or_build_natal_context",
        context_service,
    ):
        service = TodaySpherePageService(db_session, llm=llm)
        first = await service._build_natal_layer(user.id, profile, "work", "exact", profile_hash)
        second = await service._build_natal_layer(user.id, profile, "work", "exact", profile_hash)

    assert first.state == second.state == "ready"
    assert first.paragraphs and first.paragraphs[0].source_fact_ids == ["natal:planet:SUN"]
    assert llm.calls == 1
    assert "top_signals" not in llm.prompts[0]
    assert "natal:planet:SUN" in llm.prompts[0]
    assert "natal:planet:MERCURY" not in llm.prompts[0]
    assert await db_session.scalar(select(func.count()).select_from(TodaySphereNatalNarrative)) == 1
    assert context_service.await_count == 1


@pytest.mark.asyncio
async def test_natal_failure_is_unavailable_without_null_cache_row(db_session: AsyncSession) -> None:
    user = User(tg_user_id=uuid4().int % 2_000_000_000)
    profile = _profile()
    profile.user_id = user.id
    user.profile = profile
    db_session.add(user)
    await db_session.commit()

    class BadLLM:
        async def generate(self, prompt: str, *, max_output_tokens: int, timeout_seconds: float):
            return {
                "paragraphs": [
                    {
                        "text": "Сегодня появится неподтверждённый вывод.",
                        "sourceFactIds": ["natal:planet:SUN"],
                    }
                ]
            }

    profile_hash = NatalContextService.compute_profile_hash(profile)
    with patch(
        "app.services.today_sphere_page_service.NatalContextService.get_or_build_natal_context",
        AsyncMock(return_value=_context()),
    ):
        result = await TodaySpherePageService(db_session, llm=BadLLM())._build_natal_layer(
            user.id, profile, "work", "exact", profile_hash
        )

    assert result.state == "unavailable"
    assert result.paragraphs is None
    assert await db_session.scalar(select(func.count()).select_from(TodaySphereNatalNarrative)) == 0
# END_BLOCK: NATAL_CACHE_GATES
