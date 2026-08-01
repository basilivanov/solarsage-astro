# ############################################################################
# AI_HEADER: MODULE_TEST_TODAY_SERVICE_CACHE_UNIT — targeted legacy TodayService coverage.
# ROLE: Characterize live cache, preview, chart, helper, and failure branches
#       without restoring the removed HTTP wire contract.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-TODAY-SERVICE-CACHE-UNIT
# purpose: Recover focused unit coverage for live TodayService cache identity,
#   preview, pure builders, and defensive fallback branches.
# owns:
#   - apps/api/tests/test_today_service_cache_unit.py
# inputs: AsyncSession test database, real TodayService methods, deterministic
#   Pydantic payloads, and mocked external boundaries only where required.
# outputs: Characterization assertions for current TodayService behavior.
# dependencies: TodayService, today schemas/models, shared test fixtures.
# side_effects: Writes only isolated in-memory test rows through the fixture DB.
# emitted_logs: none.
# invariants:
#   - production today_service.py is not modified;
#   - tests call live service methods, not HTTP routes or copied implementations;
#   - cache predicates remain fail-closed for stale/degraded V2 rows.
# failure_policy: pytest assertion or propagated service exception on mismatch.
# END_MODULE_CONTRACT: M-TEST-TODAY-SERVICE-CACHE-UNIT

# START_MODULE_MAP: M-TEST-TODAY-SERVICE-CACHE-UNIT
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - CACHE_PREDICATES: version/content/quality cache read gates
#   - CACHE_WRITES: payload and semantic-layer insert/update paths
#   - PURE_BUILDERS: preview, chart, influence, and top-flag helpers
#   - FAILURE_PATHS: locked/invalid-profile/split-brain/yesterday fallbacks
#   - LLM_PHASE: focus input, timeout, cancellation, and narrative outcomes
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-TODAY-SERVICE-CACHE-UNIT

from __future__ import annotations

import asyncio
import json
from contextlib import ExitStack
from datetime import UTC, date as Date, datetime, time as Time
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.versions import (
    LEGACY_FRONTEND_PAYLOAD_VERSION,
    LEGACY_SCORING_VERSION,
    SCORING_V2_VERSION,
    TODAY_CONTENT_VERSION,
    TODAY_V1_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
    V2_FRONTEND_PAYLOAD_VERSION,
)
from app.db.models import SemanticLayerCache, TodayPayloadCache, User, UserProfile
from app.schemas.access import ContentAccessState
from app.schemas.natal import NatalChartHouse, NatalChartPlanet, NatalContextData
from app.schemas.normalization import AstroSignal
from app.schemas.today import (
    ReadingBody,
    TodayMeta,
    TodayPayload,
    WhyThisHappens,
)
from app.services.today_service import TodayService


TARGET_DATE = Date(2026, 7, 8)
PROFILE_HASH = "profile-hash"


# START_BLOCK: TEST_FIXTURES
async def _user_with_profile(
    db: AsyncSession,
    tg_user_id: int = 700001,
    *,
    birthday: Date | None = Date(1990, 1, 15),
    birth_tz: str | None = "Europe/Moscow",
    birth_lat: float | None = 55.7558,
    birth_lon: float | None = 37.6173,
) -> tuple[User, UserProfile]:
    user = User(tg_user_id=tg_user_id, tg_username=f"today_unit_{tg_user_id}")
    db.add(user)
    await db.flush()
    profile = UserProfile(
        user_id=user.id,
        first_name="Today unit",
        birthday=birthday,
        birth_time=Time(12, 0) if birthday is not None else None,
        birth_city="Moscow" if birthday is not None else None,
        birth_lat=birth_lat,
        birth_lon=birth_lon,
        gender="female",
        birth_tz=birth_tz,
        is_onboarded=True,
    )
    db.add(profile)
    await db.commit()
    return user, profile


def _valid_payload(*, headline: str = "Today") -> TodayPayload:
    from tests.today_test_fixtures import build_deterministic_interpretation_result

    concrete_advice, day_summary, _ = build_deterministic_interpretation_result()
    return TodayPayload(
        meta=TodayMeta(
            schema_version="today/v1",
            contract_version=3,
            calculation_version=1,
            normalization_version=1,
            scoring_version=1,
            prompt_version=2,
            content_version=TODAY_CONTENT_VERSION,
            generated_at="2026-07-08T12:00:00Z",
            cached=False,
            payload_version=TODAY_V1_PAYLOAD_VERSION,
            frontend_payload_version=LEGACY_FRONTEND_PAYLOAD_VERSION,
        ),
        date=TARGET_DATE.isoformat(),
        title="Сегодня",
        headline=headline,
        access=ContentAccessState(state="full"),
        day_status="steady",
        day_summary=day_summary,
        concrete_advice=concrete_advice,
        top_flags=[],
        reading=ReadingBody(paragraphs=["Reading"]),
        why_this_happens=WhyThisHappens(sections=[]),
        week_strip=[],
        microcopy=[],
        v2=None,
    )


def _raw_cache_payload(
    *,
    payload_version: str = TODAY_V2_PAYLOAD_VERSION,
    content_version: int = TODAY_CONTENT_VERSION,
    frontend_payload_version: int = 1,
    focus: dict | None = None,
    include_focus: bool = True,
    include_v2: bool = True,
) -> dict:
    meta = {
        "payload_version": payload_version,
        "content_version": content_version,
        "frontend_payload_version": frontend_payload_version,
    }
    payload = {"meta": meta}
    if include_focus:
        payload["focus"] = focus
    if include_v2:
        payload["v2"] = {"present": True}
    return payload


async def _cache_row(
    db: AsyncSession,
    user: User,
    payload: dict,
    *,
    target_date: Date = TARGET_DATE,
    profile_hash: str = PROFILE_HASH,
) -> TodayPayloadCache:
    row = TodayPayloadCache(
        user_id=user.id,
        target_date=target_date,
        profile_hash=profile_hash,
        payload_json=json.dumps(payload),
        cache_key_hash="",
    )
    db.add(row)
    await db.commit()
    return row


def _fake_natal_context() -> NatalContextData:
    return NatalContextData(
        house_system="WHOLE_SIGN",
        planets=[
            NatalChartPlanet(
                name="Sun",
                sign="Capricorn",
                degree=7.0,
                longitude=286.93,
                retrograde=False,
                house=11,
            )
        ],
        houses=[
            NatalChartHouse(
                number=index,
                sign="Aries",
                degree=0.0,
                longitude=float((index - 1) * 30),
            )
            for index in range(1, 13)
        ],
    )


def _fake_dual(*, selected_scoring_version: int | str = LEGACY_SCORING_VERSION) -> MagicMock:
    dual = MagicMock()
    dual.selected_scoring_version = selected_scoring_version
    dual.selected_result = {
        "day_status": "steady",
        "sphere_scores": {"career": 1.0},
        "top_signals": [],
    }
    dual.v2_result = None
    dual.diff = None
    dual.factor_ledger = []
    dual.valence_assessments = {}
    dual.valence_breakdown = SimpleNamespace(support_score=0.0, tension_score=0.0)
    return dual


def _pipeline_patches(
    *,
    focus_state: str = "background_only",
    has_llm_key: bool = False,
    wait_side_effect=None,
    llm_side_effect=None,
    interpretation_side_effect=None,
    focus_narrative_result=None,
    focus_narrative_side_effect=None,
    validator_result=None,
    deadline_seconds: float | None = None,
    why_result=None,
    dual: MagicMock | None = None,
):
    """Patch only external collaborators while leaving TodayService live."""
    stack = ExitStack()
    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value=None)
    stack.enter_context(patch("app.services.today_service.get_solarsage_client", return_value=mock_client))
    stack.enter_context(patch.object(settings, "solarsage_v2_enabled", False))
    stack.enter_context(patch.object(settings, "solarsage_v2_dual_run", False))
    stack.enter_context(patch.object(settings, "today_valence_v1_enabled", False))
    if deadline_seconds is not None:
        stack.enter_context(patch("app.services.today_service.LLM_PHASE_DEADLINE_SECONDS", deadline_seconds))
    stack.enter_context(
        patch(
            "app.services.today_service.NatalContextService.get_or_build_natal_context",
            new=AsyncMock(return_value=_fake_natal_context()),
        )
    )
    stack.enter_context(patch("app.services.today_service.NormalizationService.normalize_day", return_value=[]))
    stack.enter_context(patch.object(TodayService, "_get_yesterday_signals", new=AsyncMock(return_value=None)))
    stack.enter_context(patch.object(TodayService, "_cache_semantic_layer", new=AsyncMock()))
    stack.enter_context(patch.object(TodayService, "_cache_payload", new=AsyncMock()))

    activation_layer = MagicMock()
    activation_layer.activation_layer_version = None
    activation_layer.activations = []
    stack.enter_context(
        patch("app.services.today_service.ActivationLayerService.build", return_value=activation_layer)
    )

    runtime = MagicMock()
    runtime.compute.return_value = dual or _fake_dual()
    stack.enter_context(patch("app.services.today_service.DayScoringRuntimeService", return_value=runtime))

    semantic = MagicMock()
    semantic_layer = MagicMock()
    semantic_layer.model_dump.return_value = {}
    semantic.build_semantic_layer.return_value = semantic_layer
    semantic.build_why_contexts.return_value = []
    stack.enter_context(patch("app.services.today_service.SemanticService", return_value=semantic))

    important = MagicMock()
    important.build_items.return_value = []
    stack.enter_context(patch("app.services.today_service.TodayImportantService", return_value=important))
    stack.enter_context(patch.object(TodayService, "_build_day_chart", return_value=None))
    stack.enter_context(patch.object(TodayService, "_build_planet_influences", return_value=[]))
    stack.enter_context(patch.object(TodayService, "_build_sphere_scores", return_value=[]))

    interpretation = MagicMock()
    interpretation_result = _valid_payload()
    interpretation_tuple = (
        interpretation_result.concrete_advice,
        interpretation_result.day_summary,
        interpretation_result.day_chart,
    )

    async def build_interpretation(*args, **kwargs):
        if interpretation_side_effect is not None:
            return await interpretation_side_effect(*args, **kwargs)
        return interpretation_tuple

    interpretation.build = AsyncMock(side_effect=build_interpretation)
    stack.enter_context(
        patch("app.services.today_interpretation_service.TodayInterpretationService", return_value=interpretation)
    )

    llm = MagicMock()

    def llm_method(value):
        async def _method(*args, **kwargs):
            if llm_side_effect is not None:
                return await llm_side_effect(value, *args, **kwargs)
            return value

        return AsyncMock(side_effect=_method)

    llm.generate_headline = llm_method("Headline")
    llm.generate_reading = llm_method(["Reading"])
    llm.generate_notes = llm_method("Notes")
    llm.generate_why_sections = llm_method(
        why_result if why_result is not None else []
    )
    llm.generate_focus_narrative = AsyncMock(
        return_value=focus_narrative_result,
        side_effect=focus_narrative_side_effect,
    )
    stack.enter_context(patch("app.services.today_service.LLMService", return_value=llm))

    focus_event = SimpleNamespace(
        id="focus-event-1",
        human_title="Поворот дня",
        kind="peak",
        occurs_at=datetime(2026, 7, 8, 12, 0, tzinfo=UTC),
        local_date=TARGET_DATE,
        timezone="Europe/Moscow",
        precision="minute",
        technical_title=None,
        source_activation_ids=[],
    )
    focus_sphere = SimpleNamespace(
        key="work",
        state="convergence_today",
        relevance_rank=1,
        convergence_id="convergence-1",
        source_event_ids=["focus-event-1"],
        source_activation_ids=[],
    )
    focus_result = SimpleNamespace(
        state=focus_state,
        events=[focus_event] if focus_state == "convergence_today" else [],
        featured_spheres=[focus_sphere] if focus_state == "convergence_today" else [],
        convergence=None,
    )
    stack.enter_context(patch("app.services.today_focus_builder.normalize_factors", return_value=[]))
    stack.enter_context(patch("app.services.today_focus_builder.build_today_focus", return_value=focus_result))
    stack.enter_context(patch.object(settings, "openrouter_api_key", "test-key" if has_llm_key else ""))

    if validator_result is not None:
        validator = MagicMock()
        validator.check_focus_narrative_safety.return_value = validator_result
        stack.enter_context(
            patch("app.services.llm_claim_validator.LLMClaimValidator", return_value=validator)
        )

    if wait_side_effect is not None:
        stack.enter_context(patch("app.services.today_service.asyncio.wait", side_effect=wait_side_effect))
    return stack


async def _run_pipeline(
    db: AsyncSession,
    *,
    tg_user_id: int,
    **patch_options,
):
    user, _ = await _user_with_profile(db, tg_user_id=tg_user_id)
    service = TodayService(db)
    access_state = patch_options.pop("access_state", ContentAccessState(state="full"))
    with _pipeline_patches(**patch_options):
        payload = await service.get_today_payload(
            user_id=user.id,
            target_date=TARGET_DATE,
            access_state=access_state,
            skip_prefetch=True,
        )
    return user, payload
# END_BLOCK: TEST_FIXTURES


# START_BLOCK: CACHE_PREDICATES
@pytest.mark.asyncio
@pytest.mark.parametrize(
    "case",
    [
        "old_content",
        "missing_focus",
        "convergence_not_ready",
        "background_not_needed_mismatch",
        "invalid_focus_state",
        "missing_v2_body",
        "missing_frontend_v2_body",
    ],
)
async def test_get_cached_payload_rejects_currently_unsafe_rows(
    db_session: AsyncSession,
    case: str,
) -> None:
    user, _ = await _user_with_profile(db_session, tg_user_id=710000 + len(case))
    if case == "old_content":
        payload = _raw_cache_payload(content_version=TODAY_CONTENT_VERSION - 1)
    elif case == "missing_focus":
        payload = _raw_cache_payload(include_focus=False)
    elif case == "convergence_not_ready":
        payload = _raw_cache_payload(focus={"state": "convergence_today", "contentState": "pending"})
    elif case == "background_not_needed_mismatch":
        payload = _raw_cache_payload(focus={"state": "background_only", "contentState": "ready"})
    elif case == "invalid_focus_state":
        payload = _raw_cache_payload(focus={"state": "unavailable", "contentState": "unavailable"})
    elif case == "missing_v2_body":
        payload = _raw_cache_payload(
            focus={"state": "background_only", "contentState": "not_needed"},
            include_v2=False,
        )
    else:
        payload = _raw_cache_payload(
            payload_version=TODAY_V1_PAYLOAD_VERSION,
            frontend_payload_version=V2_FRONTEND_PAYLOAD_VERSION,
            include_focus=False,
            include_v2=False,
        )
    await _cache_row(db_session, user, payload)

    got = await TodayService(db_session)._get_cached_payload(
        user.id,
        TARGET_DATE,
        PROFILE_HASH,
    )

    assert got is None


@pytest.mark.asyncio
async def test_cache_payload_supports_insert_and_update_without_versioned_key(
    db_session: AsyncSession,
) -> None:
    user, _ = await _user_with_profile(db_session, tg_user_id=710101)
    service = TodayService(db_session)

    await service._cache_payload(user.id, TARGET_DATE, _valid_payload(), PROFILE_HASH)
    first = (
        await db_session.execute(
            select(TodayPayloadCache).where(TodayPayloadCache.user_id == user.id)
        )
    ).scalar_one()
    assert first.cache_key_hash == ""

    await service._cache_payload(
        user.id,
        TARGET_DATE,
        _valid_payload(headline="Updated"),
        PROFILE_HASH,
    )
    second = (
        await db_session.execute(
            select(TodayPayloadCache).where(TodayPayloadCache.user_id == user.id)
        )
    ).scalar_one()
    assert json.loads(second.payload_json)["headline"] == "Updated"


@pytest.mark.asyncio
async def test_cache_semantic_layer_updates_existing_row(db_session: AsyncSession) -> None:
    user, _ = await _user_with_profile(db_session, tg_user_id=710102)
    row = SemanticLayerCache(
        user_id=user.id,
        target_date=TARGET_DATE,
        semantic_json=json.dumps({"old": True}),
    )
    db_session.add(row)
    await db_session.commit()

    semantic_layer = MagicMock()
    semantic_layer.model_dump.return_value = {"day_theme": "new"}
    await TodayService(db_session)._cache_semantic_layer(
        user.id,
        TARGET_DATE,
        semantic_layer,
        PROFILE_HASH,
    )

    await db_session.refresh(row)
    assert json.loads(row.semantic_json)["semantic_layer"] == {"day_theme": "new"}


@pytest.mark.asyncio
async def test_invalidate_cache_deletes_payload_and_semantic_rows(db_session: AsyncSession) -> None:
    user, _ = await _user_with_profile(db_session, tg_user_id=710103)
    db_session.add(
        TodayPayloadCache(
            user_id=user.id,
            target_date=TARGET_DATE,
            profile_hash=PROFILE_HASH,
            payload_json="{}",
        )
    )
    db_session.add(
        SemanticLayerCache(
            user_id=user.id,
            target_date=TARGET_DATE,
            semantic_json="{}",
        )
    )
    await db_session.commit()

    await TodayService(db_session).invalidate_cache(user.id)

    assert (
        await db_session.execute(
            select(TodayPayloadCache).where(TodayPayloadCache.user_id == user.id)
        )
    ).scalar_one_or_none() is None
    assert (
        await db_session.execute(
            select(SemanticLayerCache).where(SemanticLayerCache.user_id == user.id)
        )
    ).scalar_one_or_none() is None
# END_BLOCK: CACHE_PREDICATES


# START_BLOCK: PURE_BUILDERS
def test_today_service_pure_builders_cover_empty_and_fallback_branches() -> None:
    unknown_aspect = SimpleNamespace(
        type="aspect",
        planet="",
        target_planet="",
        aspect_type="quincunx",
        strength=0.4,
    )
    ignored = SimpleNamespace(type="other", planet="", strength=0.1)
    assert TodayService._build_top_flag(unknown_aspect) is None
    assert TodayService._build_top_flag(ignored) is None
    assert TodayService._planet_label("") == "Планета"
    assert TodayService._planet_label("TRANSIT_MOON") == "Луна"
    assert TodayService._planet_label("NATAL_SATURN") == "Сатурн"
    assert TodayService._top_flag_aspect_summary("quincunx").startswith("Заметный аспект")

    assert TodayService._build_day_chart({}, {}, []) is None
    chart = TodayService._build_day_chart(
        {"houses": [{"number": 1, "cusp": 0.0, "sign": "Aries"}]},
        {
            "planets": [
                {"name": "Transit_Sun", "longitude": 10.0, "speed": 0.0, "retrograde": False},
                {"name": "Transit_Mars", "longitude": 20.0, "speed": -0.2, "retrograde": False},
                {"name": "Moon", "longitude": 30.0, "speed": 0.2, "retrograde": False},
                {"name": "Venus", "longitude": 40.0, "speed": None, "retrograde": None},
            ]
        },
        [
            AstroSignal(
                type="aspect",
                planet="Transit_Sun",
                target_planet="Natal_Moon",
                aspect_type="trine",
                orb=0.25,
                strength=0.8,
            ),
            AstroSignal(
                type="aspect",
                planet="Natal_Sun",
                target_planet="Natal_Moon",
                aspect_type="square",
                orb=0.5,
                strength=0.4,
            ),
        ],
    )
    assert chart is not None
    assert [planet.motion for planet in chart.transit_planets] == [
        "stationary",
        "retrograde",
        "direct",
        None,
    ]
    assert len(chart.aspects) == 1

    influences = TodayService._build_planet_influences(
        [
            AstroSignal(type="planet_in_house", planet="", target_planet="Natal_Moon", strength=1.0),
            AstroSignal(type="planet_in_house", planet="Transit_Sun", target_planet="", strength=0.8),
        ]
    )
    assert [influence.name for influence in influences] == ["Sun", "Moon"]
# END_BLOCK: PURE_BUILDERS


# START_BLOCK: FAILURE_PATHS
@pytest.mark.asyncio
async def test_get_today_payload_locked_uses_preview_builder(db_session: AsyncSession) -> None:
    user, _ = await _user_with_profile(db_session, tg_user_id=710201)
    service = TodayService(db_session)
    preview = _valid_payload(headline="Preview")

    with patch.object(service, "_build_preview_payload", new=AsyncMock(return_value=preview)) as builder:
        got = await service.get_today_payload(
            user.id,
            TARGET_DATE,
            ContentAccessState(state="locked", reason="outside_access_window"),
        )

    assert got is preview
    builder.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_today_payload_defaults_missing_access_to_full(db_session: AsyncSession) -> None:
    _, payload = await _run_pipeline(
        db_session,
        tg_user_id=7102011,
        access_state=None,
    )

    assert payload.access.state == "full"


@pytest.mark.asyncio
async def test_get_today_payload_rejects_missing_birth_identity(db_session: AsyncSession) -> None:
    user, _ = await _user_with_profile(
        db_session,
        tg_user_id=710202,
        birthday=None,
        birth_tz=None,
    )
    service = TodayService(db_session)

    with patch.object(service, "_get_cached_payload", new=AsyncMock(return_value=None)), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context", new=AsyncMock(return_value=_fake_natal_context())):
        with pytest.raises(RuntimeError, match="missing birth identity"):
            await service.get_today_payload(
                user.id,
                TARGET_DATE,
                ContentAccessState(state="full"),
            )


@pytest.mark.asyncio
async def test_get_yesterday_signals_fails_open_on_provider_error(db_session: AsyncSession) -> None:
    service = TodayService(db_session)
    client = AsyncMock()
    client.get_transits.side_effect = RuntimeError("sidecar unavailable")
    profile = SimpleNamespace(birth_tz=None)

    got = await service._get_yesterday_signals(
        uuid4(),
        TARGET_DATE,
        profile,
        client,
        {},
    )

    assert got is None
# END_BLOCK: FAILURE_PATHS


# START_BLOCK: LLM_PHASE
@pytest.mark.asyncio
async def test_get_today_payload_fails_closed_on_runtime_selection_split_brain(
    db_session: AsyncSession,
) -> None:
    mismatched = _fake_dual(selected_scoring_version=SCORING_V2_VERSION)

    with pytest.raises(RuntimeError, match="split-brain"):
        await _run_pipeline(
            db_session,
            tg_user_id=710301,
            dual=mismatched,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("narrative_mode", ["empty", "valid", "rejected", "error"])
async def test_get_today_payload_characterizes_focus_narrative_outcomes(
    db_session: AsyncSession,
    narrative_mode: str,
) -> None:
    options = {
        "focus_state": "convergence_today",
        "has_llm_key": True,
    }
    if narrative_mode == "valid":
        options.update(
            focus_narrative_result="validated narrative",
            why_result=[{"id": "why", "title": "Why", "blocks": []}],
            validator_result=(
                {
                    "convergence_summary": "Сводка",
                    "event_meanings": {},
                    "featured_spheres": {},
                },
                None,
            ),
        )
    elif narrative_mode == "rejected":
        options.update(
            focus_narrative_result="unsafe narrative",
            validator_result=(None, "unsupported_claim"),
        )
    elif narrative_mode == "error":
        options["focus_narrative_side_effect"] = ValueError("provider failure")

    # AsyncMock accepts an exception instance as a side_effect and raises it
    # when the focus task result is consumed by the live service.
    _, payload = await _run_pipeline(
        db_session,
        tg_user_id=710310 + ["empty", "valid", "rejected", "error"].index(narrative_mode),
        **options,
    )

    assert payload.focus is not None
    assert payload.focus.content_state == ("ready" if narrative_mode == "valid" else "unavailable")


@pytest.mark.asyncio
async def test_get_today_payload_cancels_and_awaits_deadline_tasks(db_session: AsyncSession) -> None:
    async def slow_branch(*args, **kwargs):
        if kwargs.get("force_no_llm"):
            return await _interpretation_fallback()
        await asyncio.sleep(1)
        return None

    async def slow_llm(*args, **kwargs):
        await asyncio.sleep(1)
        return None

    async def _interpretation_fallback():
        concrete, summary, chart = (
            _valid_payload().concrete_advice,
            _valid_payload().day_summary,
            _valid_payload().day_chart,
        )
        return concrete, summary, chart

    _, payload = await _run_pipeline(
        db_session,
        tg_user_id=710320,
        focus_state="convergence_today",
        llm_side_effect=slow_llm,
        interpretation_side_effect=slow_branch,
        deadline_seconds=0.001,
    )

    assert payload.headline == "Ваш персональный разбор дня"
    assert payload.focus is not None
    assert payload.focus.content_state == "unavailable"


@pytest.mark.asyncio
async def test_get_today_payload_cleans_up_tasks_when_wait_raises(
    db_session: AsyncSession,
) -> None:
    async def fail_after_tasks_get_a_turn(*args, **kwargs):
        await asyncio.sleep(0)
        raise RuntimeError("wait failed")

    with pytest.raises(RuntimeError, match="wait failed"):
        await _run_pipeline(
            db_session,
            tg_user_id=710321,
            wait_side_effect=fail_after_tasks_get_a_turn,
        )
# END_BLOCK: LLM_PHASE
