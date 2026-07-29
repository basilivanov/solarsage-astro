"""Tests: W5 versioned cache key."""
import uuid
import json
from copy import deepcopy
from datetime import date as Date, time as Time
from datetime import datetime, UTC
from pathlib import Path

import pytest
from sqlalchemy import select

from app.services.cache_key_service import (
    build_today_cache_key, expected_cache_identity, resolve_today_runtime_identity,
    TodayRuntimeIdentity,
)
from app.db.models import TodayPayloadCache, SemanticLayerCache, User, UserProfile
from app.schemas.today import TodayPayload, TodayMeta, DaySummaryBlock, ConcreteAdviceBlock, ConcreteAdviceCounts, TodayV2Block
from app.schemas.today_focus import TodayFocus, TodayFocusEvent, TodayFeaturedSphere, TodayConvergence, TodayFocusFactor
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService, TODAY_CONTENT_VERSION
from app.services.calendar_service import CalendarService
from app.services.cache_key_service import get_canon_versions
from app.core.versions import (
    ACTIVATION_LAYER_VERSION,
    CALCULATION_VERSION,
    LEGACY_CALCULATION_VERSION,
    LEGACY_FRONTEND_PAYLOAD_VERSION,
    LEGACY_SCORING_VERSION,
    SCORING_V2_VERSION,
    TODAY_V1_PAYLOAD_VERSION,
    TODAY_V2_PAYLOAD_VERSION,
    V2_FRONTEND_PAYLOAD_VERSION,
)


def make_minimal_today_payload(target_date: Date) -> TodayPayload:
    access_state = ContentAccessState(state="preview", reason="expired_access")
    return TodayPayload(
        meta=TodayMeta(
            schema_version="today/v1",
            contract_version=3,
            calculation_version=1,
            normalization_version=1,
            scoring_version=1,
            prompt_version=2,
            content_version=TODAY_CONTENT_VERSION,
            generated_at=datetime.now(UTC).isoformat(),
            cached=False,
            canon_versions=get_canon_versions(),
        ),
        date=target_date.isoformat(),
        title="Сегодня",
        headline="Этот день доступен по подписке",
        access=access_state.model_dump(),
        day_status="steady",
        day_summary=DaySummaryBlock(
            status_label="День заблокирован",
            status_line="Подпишитесь, чтобы увидеть разбор",
            facts=[]
        ),
        concrete_advice=ConcreteAdviceBlock(
            rows=[],
            counts=ConcreteAdviceCounts(good=0, caution=0, avoid=0, neutral=0)
        ),
        top_flags=[],
        reading={"paragraphs": []},
        why_this_happens={"sections": []},
        week_strip=[],
        microcopy=[],
    )


# ── Pure hash construction ───────────────────────────────────────────────


def test_cache_key_different_scoring_versions():
    """Different scoring_version produces different cache_key_hash."""
    uid = uuid.uuid4()
    k1 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", scoring_version=1)
    k2 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", scoring_version="ss-scoring-2.0")
    assert k1.cache_key_hash != k2.cache_key_hash


def test_cache_key_different_profiles():
    """Different profile_hash produces different cache_key_hash."""
    uid = uuid.uuid4()
    k1 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc")
    k2 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="xyz")
    assert k1.cache_key_hash != k2.cache_key_hash


def test_cache_key_activation_layer_version_affects_hash():
    """activation_layer_version=None and 'al-1.0' produce different hashes."""
    uid = uuid.uuid4()
    k1 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", activation_layer_version=None)
    k2 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", activation_layer_version="al-1.0")
    assert k1.cache_key_hash != k2.cache_key_hash


def test_cache_key_different_activation_versions():
    """Different non-null activation_layer_version values produce different hashes."""
    uid = uuid.uuid4()
    k1 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", activation_layer_version="al-1.0")
    k2 = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc", activation_layer_version="al-2.0")
    assert k1.cache_key_hash != k2.cache_key_hash


def test_expected_cache_identity_has_non_none_al_version():
    """expected_cache_identity() has non-None activation_layer_version."""
    uid = uuid.uuid4()
    k = expected_cache_identity(user_id=uid, target_date="2026-07-08", profile_hash="abc")
    assert k.activation_layer_version is not None, "expected_cache_identity must have non-None activation_layer_version"
    assert k.activation_layer_version == "al-1.1"


def test_cache_key_field_consistency():
    """All fields are reflected in cache_key_hash."""
    uid = uuid.uuid4()
    k = build_today_cache_key(
        user_id=uid,
        target_date="2026-07-08",
        profile_hash="abc",
        calculation_version="1",
        activation_layer_version="al-1.0",
        scoring_version=1,
        llm_prompt_version=3,
        frontend_payload_version=1,
    )
    assert k.user_id == uid
    assert k.target_date == "2026-07-08"
    assert k.profile_hash == "abc"
    assert k.calculation_version == "1"
    assert k.activation_layer_version == "al-1.0"
    assert k.scoring_version == 1
    assert k.llm_prompt_version == 3
    assert k.content_version == TODAY_CONTENT_VERSION
    assert k.frontend_payload_version == 1


def test_cache_key_content_and_frontend_versions_affect_hash():
    uid = uuid.uuid4()
    base = build_today_cache_key(
        user_id=uid,
        target_date="2026-07-08",
        profile_hash="abc",
        content_version=9,
        frontend_payload_version=2,
    )
    content_changed = build_today_cache_key(
        user_id=uid,
        target_date="2026-07-08",
        profile_hash="abc",
        content_version=10,
        frontend_payload_version=2,
    )
    frontend_changed = build_today_cache_key(
        user_id=uid,
        target_date="2026-07-08",
        profile_hash="abc",
        content_version=9,
        frontend_payload_version=3,
    )
    assert base.cache_key_hash != content_changed.cache_key_hash
    assert base.cache_key_hash != frontend_changed.cache_key_hash


@pytest.mark.parametrize(
    "horizon_key",
    [
        "horizon_selection",
        "horizon_language_ru",
        "horizon_actions_ru",
        "personal_patterns_ru",
    ],
)
def test_each_horizon_canon_version_changes_both_cache_hashes(monkeypatch, horizon_key):
    import app.services.cache_key_service as cache_keys

    uid = uuid.uuid4()
    base_versions = get_canon_versions()
    monkeypatch.setattr(cache_keys, "get_canon_versions", lambda: dict(base_versions))
    base = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc")

    changed_versions = {**base_versions, horizon_key: f"{base_versions[horizon_key]}-changed"}
    monkeypatch.setattr(cache_keys, "get_canon_versions", lambda: dict(changed_versions))
    changed = build_today_cache_key(user_id=uid, target_date="2026-07-08", profile_hash="abc")

    assert base.canon_versions_hash != changed.canon_versions_hash
    assert base.cache_key_hash != changed.cache_key_hash


# ── DB-level cache identity ──────────────────────────────────────────────


def _current_fixture_payload() -> dict:
    fixture_path = (
        Path(__file__).resolve().parents[3]
        / "e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json"
    )
    return json.loads(fixture_path.read_text(encoding="utf-8"))


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("case", "tg_user_id"),
    [
        ("missing_pipeline_audit", 99701),
        ("current_payload_previous_frontend", 99702),
        ("previous_payload_current_frontend", 99703),
    ],
)
async def test_invalid_current_cache_rows_are_misses_without_exception(
    db_session,
    case,
    tg_user_id,
):
    from app.core.versions import (
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
        SCORING_V2_VERSION,
        V2_FRONTEND_PAYLOAD_VERSION,
    )

    user = User(tg_user_id=tg_user_id)
    db_session.add(user)
    await db_session.flush()
    profile_hash = "current-invalid-row"
    key = build_today_cache_key(
        user_id=user.id,
        target_date="2026-07-08",
        profile_hash=profile_hash,
        calculation_version=CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        scoring_version=SCORING_V2_VERSION,
        frontend_payload_version=V2_FRONTEND_PAYLOAD_VERSION,
    )
    payload = deepcopy(_current_fixture_payload())
    if case == "missing_pipeline_audit":
        del payload["v2"]["audit"]["horizonPipeline"]
    elif case == "current_payload_previous_frontend":
        payload["meta"]["frontendPayloadVersion"] = 2
    else:
        payload["meta"]["payloadVersion"] = "today.v2"
        payload["v2"]["audit"]["payloadVersion"] = "today.v2"

    db_session.add(
        TodayPayloadCache(
            user_id=user.id,
            target_date=Date(2026, 7, 8),
            profile_hash=profile_hash,
            cache_key_hash=key.cache_key_hash,
            payload_json=json.dumps(payload),
        )
    )
    await db_session.commit()

    result = await TodayService(db_session)._get_cached_payload(
        user.id,
        Date(2026, 7, 8),
        profile_hash,
        cache_key=key,
    )
    assert result is None


@pytest.mark.asyncio
async def test_cache_duplicate_rows_different_hash_no_multiple_results(db_session):
    """Two TodayPayloadCache rows with same user/date/profile but different
    cache_key_hash do not raise MultipleResultsFound on versioned lookup."""
    user = User(tg_user_id=99991)
    db_session.add(user)
    await db_session.flush()

    ck_v1 = build_today_cache_key(user_id=user.id, target_date="2026-07-08", profile_hash="abc", scoring_version=1)
    ck_v2 = build_today_cache_key(user_id=user.id, target_date="2026-07-08", profile_hash="abc", scoring_version="ss-scoring-2.0")

    p1 = make_minimal_today_payload(Date(2026, 7, 8))
    p1.headline = "V1 Payload"
    p2 = make_minimal_today_payload(Date(2026, 7, 8))
    p2.headline = "V2 Payload"

    db_session.add_all([
        TodayPayloadCache(user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="abc",
                          cache_key_hash=ck_v1.cache_key_hash, payload_json=p1.model_dump_json()),
        TodayPayloadCache(user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="abc",
                          cache_key_hash=ck_v2.cache_key_hash, payload_json=p2.model_dump_json()),
    ])
    await db_session.commit()

    service = TodayService(db_session)
    # Lookup with V1 key should return exactly the V1 row (no exception)
    payload = await service._get_cached_payload(user.id, Date(2026, 7, 8), "abc", cache_key=ck_v1)
    assert payload is not None
    assert payload.headline == "V1 Payload"
    assert payload.meta.cached is True


@pytest.mark.asyncio
async def test_stale_empty_hash_row_misses(db_session):
    """Old row with empty cache_key_hash misses when querying by current hash."""
    user = User(tg_user_id=99992)
    db_session.add(user)
    await db_session.flush()

    ck = expected_cache_identity(user_id=user.id, target_date="2026-07-08", profile_hash="abc")

    # Insert row with empty hash and a valid payload
    p = make_minimal_today_payload(Date(2026, 7, 8))
    db_session.add(TodayPayloadCache(
        user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="abc",
        cache_key_hash="", payload_json=p.model_dump_json(),
    ))
    await db_session.commit()

    service = TodayService(db_session)
    payload = await service._get_cached_payload(user.id, Date(2026, 7, 8), "abc", cache_key=ck)
    assert payload is None, "Stale empty-hash row must not match current key"


@pytest.mark.asyncio
async def test_payload_cache_upsert_updates_matching_hash(db_session):
    """_cache_payload with a cache_key updates only matching hash row."""
    user = User(tg_user_id=99993)
    db_session.add(user)
    await db_session.flush()

    ck_v1 = build_today_cache_key(user_id=user.id, target_date="2026-07-08", profile_hash="abc", scoring_version=1)
    ck_v2 = build_today_cache_key(user_id=user.id, target_date="2026-07-08", profile_hash="abc", scoring_version="ss-scoring-2.0")

    p_old = make_minimal_today_payload(Date(2026, 7, 8))
    p_old.headline = "Old Payload"

    db_session.add_all([
        TodayPayloadCache(user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="abc",
                          cache_key_hash=ck_v1.cache_key_hash, payload_json=p_old.model_dump_json()),
        TodayPayloadCache(user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="abc",
                          cache_key_hash=ck_v2.cache_key_hash, payload_json=p_old.model_dump_json()),
    ])
    await db_session.commit()

    service = TodayService(db_session)
    p_new = make_minimal_today_payload(Date(2026, 7, 8))
    p_new.headline = "New Updated Payload"

    # Call _cache_payload to update ck_v1
    await service._cache_payload(user.id, Date(2026, 7, 8), p_new, "abc", cache_key=ck_v1)

    # Verify that the ck_v1 row was updated
    r1 = await db_session.execute(
        select(TodayPayloadCache).where(
            TodayPayloadCache.user_id == user.id,
            TodayPayloadCache.target_date == Date(2026, 7, 8),
            TodayPayloadCache.profile_hash == "abc",
            TodayPayloadCache.cache_key_hash == ck_v1.cache_key_hash,
        )
    )
    row1 = r1.scalar_one()
    data1 = json.loads(row1.payload_json)
    assert data1["headline"] == "New Updated Payload"

    # Verify that the ck_v2 row was NOT updated
    r2 = await db_session.execute(
        select(TodayPayloadCache).where(
            TodayPayloadCache.user_id == user.id,
            TodayPayloadCache.target_date == Date(2026, 7, 8),
            TodayPayloadCache.profile_hash == "abc",
            TodayPayloadCache.cache_key_hash == ck_v2.cache_key_hash,
        )
    )
    row2 = r2.scalar_one()
    data2 = json.loads(row2.payload_json)
    assert data2["headline"] == "Old Payload"


@pytest.mark.asyncio
async def test_calendar_cache_identity_today_payload_cache_key_hash_miss(db_session):
    """CalendarService cached lookup misses if TodayPayloadCache has wrong cache_key_hash."""
    user = User(tg_user_id=99994)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id, first_name="Test",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.76, birth_lon=37.62,
        gender="female", birth_tz="Europe/Moscow", is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    # Create TodayPayloadCache row with a different cache_key_hash
    db_session.add(TodayPayloadCache(
        user_id=user.id, target_date=Date(2026, 7, 8), profile_hash="profile-hash-placeholder",
        cache_key_hash="wrong-hash", payload_json=json.dumps({
            "meta": {"contentVersion": TODAY_CONTENT_VERSION},
            "dayStatus": "tense",
        }),
    ))
    await db_session.commit()

    service = CalendarService(db_session)
    await service._prepare_request_context(user.id)
    # The expected profile hash calculated by prepare_request_context will be the real one,
    # so we overwrite it to match the row's profile_hash but keep the hash wrong.
    service._request_profile_hash = "profile-hash-placeholder"
    status = await service._get_cached_day_status(user.id, Date(2026, 7, 8))
    assert status is None


@pytest.mark.asyncio
async def test_calendar_cache_identity_semantic_layer_wrong_activation_version_miss(db_session):
    """CalendarService cached lookup misses if SemanticLayerCache has wrong activation_layer_version."""
    user = User(tg_user_id=99995)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id, first_name="Test",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.76, birth_lon=37.62,
        gender="female", birth_tz="Europe/Moscow", is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    service = CalendarService(db_session)
    await service._prepare_request_context(user.id)
    p_hash = service._request_profile_hash

    ck = expected_cache_identity(user_id=user.id, target_date="2026-07-08", profile_hash=p_hash)

    # Insert a SemanticLayerCache with mismatching activation_layer_version
    cache_data = {
        "profile_hash": p_hash,
        "content_version": TODAY_CONTENT_VERSION,
        "cache_key_hash": ck.cache_key_hash,
        "calculation_version": ck.calculation_version,
        "activation_layer_version": "wrong-activation-version",  # Mismatch!
        "scoring_version": str(ck.scoring_version),
        "canon_versions_hash": ck.canon_versions_hash,
        "llm_prompt_version": ck.llm_prompt_version,
        "frontend_payload_version": ck.frontend_payload_version,
        "semantic_layer": {"day_status": "supportive"}
    }
    db_session.add(SemanticLayerCache(
        user_id=user.id, target_date=Date(2026, 7, 8),
        semantic_json=json.dumps(cache_data),
    ))
    await db_session.commit()

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 8))
    assert status is None


@pytest.mark.asyncio
async def test_calendar_cache_identity_semantic_layer_matching_hit(db_session):
    """CalendarService cached lookup hits if SemanticLayerCache matches expected cache identity."""
    user = User(tg_user_id=99996)
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id, first_name="Test",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.76, birth_lon=37.62,
        gender="female", birth_tz="Europe/Moscow", is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    service = CalendarService(db_session)
    await service._prepare_request_context(user.id)
    p_hash = service._request_profile_hash

    ck = expected_cache_identity(user_id=user.id, target_date="2026-07-08", profile_hash=p_hash)

    # Insert a SemanticLayerCache with matching expected cache identity
    cache_data = {
        "profile_hash": p_hash,
        "content_version": TODAY_CONTENT_VERSION,
        "cache_key_hash": ck.cache_key_hash,
        "calculation_version": ck.calculation_version,
        "activation_layer_version": ck.activation_layer_version,
        "scoring_version": str(ck.scoring_version),
        "canon_versions_hash": ck.canon_versions_hash,
        "llm_prompt_version": ck.llm_prompt_version,
        "frontend_payload_version": ck.frontend_payload_version,
        "semantic_layer": {"day_status": "supportive"}
    }
    db_session.add(SemanticLayerCache(
        user_id=user.id, target_date=Date(2026, 7, 8),
        semantic_json=json.dumps(cache_data),
    ))
    await db_session.commit()

    status = await service._get_cached_day_status(user.id, Date(2026, 7, 8))
    assert status == "supportive"


def test_expected_cache_identity_v2_frontend_off_uses_v2_frontend_version(monkeypatch):
    from app.core.config import settings
    from app.core.versions import (
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
        SCORING_V2_VERSION,
        V2_FRONTEND_PAYLOAD_VERSION,
    )

    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", False)
    uid = uuid.uuid4()
    key = expected_cache_identity(user_id=uid, target_date="2026-07-08", profile_hash="abc")
    assert str(key.scoring_version) == SCORING_V2_VERSION
    assert key.calculation_version == CALCULATION_VERSION
    assert key.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert key.frontend_payload_version == V2_FRONTEND_PAYLOAD_VERSION


def test_expected_cache_identity_v1_uses_legacy_identity(monkeypatch):
    from app.core.config import settings
    from app.core.versions import (
        LEGACY_CALCULATION_VERSION,
        LEGACY_FRONTEND_PAYLOAD_VERSION,
        LEGACY_SCORING_VERSION,
    )

    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)  # must not matter
    uid = uuid.uuid4()
    key = expected_cache_identity(user_id=uid, target_date="2026-07-08", profile_hash="abc")
    assert key.scoring_version == LEGACY_SCORING_VERSION
    assert key.calculation_version == LEGACY_CALCULATION_VERSION
    assert key.frontend_payload_version == LEGACY_FRONTEND_PAYLOAD_VERSION


@pytest.mark.asyncio
async def test_cache_read_identity_matches_todayservice_write_for_v2_frontend_off(db_session, monkeypatch):
    """Read key (expected_cache_identity) must match write key fields for V2 frontend-off."""
    from datetime import date as Date, time as Time
    from unittest.mock import AsyncMock, patch

    from app.core.config import settings
    from app.core.versions import (
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
        SCORING_V2_VERSION,
        V2_FRONTEND_PAYLOAD_VERSION,
    )
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.schemas.natal import NatalChartHouse, NatalChartPlanet, NatalContextData
    from app.schemas.normalization import AstroSignal
    from app.schemas.scoring_v2 import ScoringV2Result, SphereContribution, SphereScoreV2
    from app.services.cache_key_service import expected_cache_identity
    from app.services.day_scoring_runtime_service import DualRunResult
    from app.services.natal_context_service import NatalContextService
    from app.services.today_service import TodayService

    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", False)

    user = User(tg_user_id=828282, tg_username="test_cache_rw")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id,
        first_name="Test",
        birthday=Date(1990, 1, 15),
        birth_time=Time(12, 0),
        birth_city="Moscow",
        birth_lat=55.76,
        birth_lon=37.62,
        gender="female",
        birth_tz="Europe/Moscow",
        is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    signals = [
        AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Pluto",
                    aspect_type="opposition", orb=1.0, strength=0.9)
    ]
    fake_natal = NatalContextData(
        house_system="WHOLE_SIGN",
        planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)],
        houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)],
    )
    sidecar_layer = {
        "schema_version": "activation-layer.v1",
        "activation_layer_version": ACTIVATION_LAYER_VERSION,
        "calculation_version": CALCULATION_VERSION,
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [{
            "id": "t2n__MOON__PLUTO",
            "technique": "transit_to_natal",
            "technique_family": "transit",
            "target_type": "planet",
            "target_key": "PLUTO",
            "kind": "aspect",
            "strength": 0.9,
            "evidence": "test",
            "phase": "background",
            "polarity": "tense",
        }],
        "by_planet": {"PLUTO": ["t2n__MOON__PLUTO"]},
        "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    }
    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})
    mock_client.get_activation_layer = AsyncMock(return_value=sidecar_layer)

    v1_result = {"day_status": "steady", "sphere_scores": {"documents": 1.0}, "top_signals": signals[:1]}
    v2_result = ScoringV2Result(
        scoring_version=SCORING_V2_VERSION,
        canon_versions={"spheres": "v1"},
        day_status="steady",
        status_breakdown={"rule": "test"},
        sphere_scores={
            "documents": SphereScoreV2(
                key="documents", title="Documents",
                base_score=1.0, activation_score=0.5, convergence_bonus=0.0,
                raw_score=1.5, final_score=1.5, normalized_score=None,
                dominance_capped=False,
                contributions=[SphereContribution(
                    sphere="documents", source="activation",
                    source_id="t2n__MOON__PLUTO", amount=0.5, evidence="test",
                )],
            )
        },
        top_signals=[], top_activations=[], debug={},
    )
    dual = DualRunResult(
        selected_result=v1_result,
        selected_scoring_version=SCORING_V2_VERSION,
        v1_result=v1_result,
        v2_result=v2_result,
        diff=None, v2_error=None,
    )

    write_keys = []
    async def capture_write(self, *args, **kwargs):
        if len(args) >= 5:
            write_keys.append(args[4])
        elif "cache_key" in kwargs:
            write_keys.append(kwargs["cache_key"])

    from app.schemas.horizon_pipeline import HorizonPipelineResult
    from app.schemas.horizon_selection import HorizonSelectionDiagnostics

    class IntegrationSpy:
        def __init__(self):
            self.calls = []

        def build(self, **kwargs):
            self.calls.append(kwargs)
            return HorizonPipelineResult(
                status="unavailable",
                horizons=None,
                selection_reason="missing_long",
                selection_diagnostics=HorizonSelectionDiagnostics(
                    input_count=1,
                    active_count=1,
                    classified_count=1,
                    candidate_count=0,
                    per_horizon_pre_bound_counts={"long": 0, "medium": 0, "fast": 0},
                    per_horizon_post_bound_counts={"long": 0, "medium": 0, "fast": 0},
                    excluded_counts_by_reason={},
                    combinations_evaluated=0,
                ),
            )

    integration_spy = IntegrationSpy()

    # The cache identity proof needs a CACHEABLE payload and must NOT depend
    # on wall-clock: the interpretation internals are irrelevant to scoring/
    # cache read-write identity, so the whole build is mocked with a
    # contract-valid deterministic tuple (12 non-fallback rows). Production
    # deadline and no-deadline-cache policy stay untouched.
    from tests.today_test_fixtures import build_deterministic_interpretation_result

    interpretation_result = build_deterministic_interpretation_result()

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context", AsyncMock(return_value=fake_natal)), \
         patch("app.services.today_service.NormalizationService.normalize_day", return_value=signals), \
         patch.object(TodayService, "_get_yesterday_signals", AsyncMock(return_value=None)), \
         patch.object(TodayService, "_cache_payload", new=capture_write), \
         patch.object(TodayService, "_cache_semantic_layer", AsyncMock()), \
         patch("app.services.today_service.DayScoringRuntimeService.compute", return_value=dual), \
         patch("app.services.today_interpretation_service.TodayInterpretationService") as MockInterpretation:
        MockInterpretation.return_value.build = AsyncMock(return_value=interpretation_result)
        service = TodayService(db_session, horizon_integration_service=integration_spy)
        access = ContentAccessState(state="preview", reason="expired_access")
        await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

    MockInterpretation.return_value.build.assert_awaited_once()

    assert len(integration_spy.calls) == 1
    assert integration_spy.calls[0]["activation_layer"].activation_layer_version == ACTIVATION_LAYER_VERSION
    assert integration_spy.calls[0]["scoring_result"] is v2_result
    assert integration_spy.calls[0]["natal_context"] is fake_natal

    profile_hash = NatalContextService.compute_profile_hash(profile)
    read_key = expected_cache_identity(
        user_id=user.id, target_date="2026-07-08", profile_hash=profile_hash,
    )
    assert write_keys, "expected write cache key"
    write_key = write_keys[0]
    assert str(read_key.scoring_version) == str(write_key.scoring_version) == SCORING_V2_VERSION
    assert read_key.calculation_version == write_key.calculation_version == CALCULATION_VERSION
    assert read_key.activation_layer_version == write_key.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert read_key.content_version == write_key.content_version == TODAY_CONTENT_VERSION
    assert read_key.frontend_payload_version == write_key.frontend_payload_version == V2_FRONTEND_PAYLOAD_VERSION
    assert read_key.cache_key_hash == write_key.cache_key_hash


class TestRuntimeIdentityResolver:
    """Prove resolve_today_runtime_identity is the single canonical family mapper."""

    def test_v1_selected_maps_to_legacy_family(self):
        """V1 selected + any activation object → legacy calculation/scoring/frontend/payload."""
        identity = resolve_today_runtime_identity(
            selected_scoring_version=LEGACY_SCORING_VERSION,
            activation_layer_version="custom-al-v1",
        )
        assert identity.calculation_version == LEGACY_CALCULATION_VERSION
        assert identity.scoring_version == LEGACY_SCORING_VERSION
        assert identity.payload_version == TODAY_V1_PAYLOAD_VERSION
        assert identity.frontend_payload_version == LEGACY_FRONTEND_PAYLOAD_VERSION
        assert identity.content_version == TODAY_CONTENT_VERSION
        assert identity.activation_layer_version == "custom-al-v1"

    def test_v2_selected_maps_to_current_family(self):
        """V2 selected → current calculation/scoring/frontend/payload family."""
        identity = resolve_today_runtime_identity(
            selected_scoring_version=SCORING_V2_VERSION,
            activation_layer_version=ACTIVATION_LAYER_VERSION,
        )
        assert identity.calculation_version == CALCULATION_VERSION
        assert identity.scoring_version == SCORING_V2_VERSION
        assert identity.payload_version == TODAY_V2_PAYLOAD_VERSION
        assert identity.frontend_payload_version == V2_FRONTEND_PAYLOAD_VERSION
        assert identity.content_version == TODAY_CONTENT_VERSION
        assert identity.activation_layer_version == ACTIVATION_LAYER_VERSION

    def test_read_write_hash_parity_v1(self, monkeypatch):
        """V1 expected_cache_identity hash equals build_today_cache_key from resolver."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
        uid = uuid.uuid4()
        ident = resolve_today_runtime_identity(
            selected_scoring_version=LEGACY_SCORING_VERSION,
        )
        read_key = expected_cache_identity(
            user_id=uid, target_date="2026-07-08", profile_hash="p1",
        )
        write_key = build_today_cache_key(
            user_id=uid,
            target_date="2026-07-08",
            profile_hash="p1",
            calculation_version=ident.calculation_version,
            activation_layer_version=ident.activation_layer_version,
            scoring_version=ident.scoring_version,
            content_version=ident.content_version,
            frontend_payload_version=ident.frontend_payload_version,
        )
        assert read_key.cache_key_hash == write_key.cache_key_hash

    def test_read_write_hash_parity_v2(self, monkeypatch):
        """V2 expected_cache_identity hash equals build_today_cache_key from resolver."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
        uid = uuid.uuid4()
        ident = resolve_today_runtime_identity(
            selected_scoring_version=SCORING_V2_VERSION,
        )
        read_key = expected_cache_identity(
            user_id=uid, target_date="2026-07-08", profile_hash="p2",
        )
        write_key = build_today_cache_key(
            user_id=uid,
            target_date="2026-07-08",
            profile_hash="p2",
            calculation_version=ident.calculation_version,
            activation_layer_version=ident.activation_layer_version,
            scoring_version=ident.scoring_version,
            content_version=ident.content_version,
            frontend_payload_version=ident.frontend_payload_version,
        )
        assert read_key.cache_key_hash == write_key.cache_key_hash

    def test_frontend_flag_does_not_alter_v1_identity(self, monkeypatch):
        """Frontend flag true while V1 is selected does not alter identity."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
        monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)
        uid = uuid.uuid4()
        read_key = expected_cache_identity(
            user_id=uid, target_date="2026-07-08", profile_hash="p3",
        )
        ident = resolve_today_runtime_identity(
            selected_scoring_version=LEGACY_SCORING_VERSION,
        )
        # Verify V1 family from both read identity and resolver
        assert read_key.calculation_version == ident.calculation_version == LEGACY_CALCULATION_VERSION
        assert read_key.scoring_version == ident.scoring_version == LEGACY_SCORING_VERSION
        assert read_key.frontend_payload_version == ident.frontend_payload_version == LEGACY_FRONTEND_PAYLOAD_VERSION
        # Hash parity: read key matches a write key built from the same identity
        write_key = build_today_cache_key(
            user_id=uid,
            target_date="2026-07-08",
            profile_hash="p3",
            calculation_version=ident.calculation_version,
            activation_layer_version=ident.activation_layer_version,
            scoring_version=ident.scoring_version,
            content_version=ident.content_version,
            frontend_payload_version=ident.frontend_payload_version,
        )
        assert read_key.cache_key_hash == write_key.cache_key_hash

    def test_dual_run_does_not_alter_v1_identity(self, monkeypatch):
        """Dual-run true while V1 is selected does not alter identity."""
        from app.core.config import settings
        monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
        monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
        uid = uuid.uuid4()
        read_key = expected_cache_identity(
            user_id=uid, target_date="2026-07-08", profile_hash="p4",
        )
        ident = resolve_today_runtime_identity(
            selected_scoring_version=LEGACY_SCORING_VERSION,
        )
        assert read_key.calculation_version == ident.calculation_version == LEGACY_CALCULATION_VERSION
        assert read_key.scoring_version == ident.scoring_version == LEGACY_SCORING_VERSION
        # Hash parity: read and write identities match under V1 selection
        write_key = build_today_cache_key(
            user_id=uid,
            target_date="2026-07-08",
            profile_hash="p4",
            calculation_version=ident.calculation_version,
            activation_layer_version=ident.activation_layer_version,
            scoring_version=ident.scoring_version,
            content_version=ident.content_version,
            frontend_payload_version=ident.frontend_payload_version,
        )
        assert read_key.cache_key_hash == write_key.cache_key_hash

    def test_activation_layer_version_preserved_when_non_null(self):
        """Supplied activation-layer version is preserved."""
        ident = resolve_today_runtime_identity(
            selected_scoring_version=SCORING_V2_VERSION,
            activation_layer_version="al-custom-42",
        )
        assert ident.activation_layer_version == "al-custom-42"

    def test_activation_layer_version_fallback_when_null(self):
        """Null activation-layer version uses canonical fallback."""
        ident = resolve_today_runtime_identity(
            selected_scoring_version=SCORING_V2_VERSION,
        )
        assert ident.activation_layer_version == ACTIVATION_LAYER_VERSION

    def test_resolver_result_is_immutable(self):
        """TodayRuntimeIdentity is frozen and cannot be mutated."""
        identity = resolve_today_runtime_identity(
            selected_scoring_version=LEGACY_SCORING_VERSION,
        )
        assert isinstance(identity, TodayRuntimeIdentity)
        with pytest.raises(AttributeError):
            identity.calculation_version = "changed"


@pytest.mark.asyncio
async def test_today_cache_quality_predicate_and_parity(db_session):
    """Verify cache quality matrix (§6.7) and fresh-vs-cached parity (§6.8)."""
    uid = uuid.uuid4()
    target_date = Date(2026, 7, 28)
    profile_hash = "prof_hash_test"
    service = TodayService(db_session)

    cache_key = build_today_cache_key(
        user_id=uid,
        target_date="2026-07-28",
        profile_hash=profile_hash,
        scoring_version=SCORING_V2_VERSION,
    )

    base_payload = make_minimal_today_payload(target_date)
    base_payload.meta.payload_version = TODAY_V2_PAYLOAD_VERSION
    base_payload.meta.frontend_payload_version = V2_FRONTEND_PAYLOAD_VERSION
    base_payload.meta.content_version = TODAY_CONTENT_VERSION
    v2_dummy = TodayV2Block(
        activation_summary={"headline": "H", "top_activated_targets": []},
        activation_evidence=[],
        score_breakdown={},
        why_today=[],
        audit={
            "available": False,
            "payload_version": TODAY_V2_PAYLOAD_VERSION,
            "calculation_version": "1",
            "scoring_version": "1",
            "canon_versions": {},
            "horizon_pipeline": {"status": "unavailable", "reason": "no_coherent_triple", "selected_count": 0},
        },
    )
    base_payload.v2 = v2_dummy

    # Helper to test cache read for raw focus dict bypassing model validation to simulate corrupted/legacy cache payload_json
    async def _check_cache_raw(focus_dict: dict | None) -> TodayPayload | None:
        p_dict = base_payload.model_dump(by_alias=True)
        p_dict["meta"]["payloadVersion"] = TODAY_V2_PAYLOAD_VERSION
        p_dict["meta"]["frontendPayloadVersion"] = V2_FRONTEND_PAYLOAD_VERSION
        p_dict["meta"]["contentVersion"] = TODAY_CONTENT_VERSION
        p_dict["focus"] = focus_dict
        p_json = json.dumps(p_dict)

        result = await db_session.execute(
            select(TodayPayloadCache).where(
                TodayPayloadCache.user_id == uid,
                TodayPayloadCache.target_date == target_date,
                TodayPayloadCache.profile_hash == profile_hash,
            )
        )
        existing = result.scalar_one_or_none()
        if existing:
            existing.payload_json = p_json
            existing.cache_key_hash = cache_key.cache_key_hash
        else:
            entry = TodayPayloadCache(
                user_id=uid,
                target_date=target_date,
                profile_hash=profile_hash,
                payload_json=p_json,
                cache_key_hash=cache_key.cache_key_hash,
                calculation_version="1",
                scoring_version="ss-scoring-2.0",
                canon_versions_hash="",
                llm_prompt_version=4,
                frontend_payload_version=4,
            )
            db_session.add(entry)
        await db_session.commit()

        # Pass cache_key with matching expected identity
        return await service._get_cached_payload(uid, target_date, profile_hash, cache_key)

    # 1. Missing focus -> MISS
    res = await _check_cache_raw(None)
    assert res is None

    # 2. convergence_today + contentState=unavailable -> MISS
    res = await _check_cache_raw({"state": "convergence_today", "contentState": "unavailable", "events": []})
    assert res is None

    # 3. convergence_today + contentState=pending -> MISS
    res = await _check_cache_raw({"state": "convergence_today", "contentState": "pending", "events": []})
    assert res is None

    # 4. background_only + contentState=ready -> MISS
    res = await _check_cache_raw({"state": "background_only", "contentState": "ready", "events": []})
    assert res is None

    # 5. background_only + contentState=not_needed -> HIT
    res = await _check_cache_raw({"state": "background_only", "contentState": "not_needed", "events": []})
    assert res is not None
    assert res.focus.state == "background_only"

    # 6. convergence_today + contentState=ready -> HIT & Parity check
    focus_ready = {
        "state": "convergence_today",
        "contentState": "ready",
        "convergence": {
            "id": "conv:1",
            "themeKey": "PLUTO",
            "title": "Схождение",
            "summary": "Разбор",
            "independentFactorCount": 2,
            "techniqueFamilies": ["transit"],
            "sourceActivationIds": ["act-1"],
            "backgroundFactors": [],
        },
        "events": [
            {
                "id": "ev:1",
                "kind": "exact",
                "occursAt": "2026-07-28T10:31:00Z",
                "localDate": "2026-07-28",
                "timezone": "Europe/Moscow",
                "precision": "minute",
                "humanTitle": "Событие 1",
                "meaning": "Смысл 1",
                "sourceActivationIds": ["act-1"],
            }
        ],
        "featuredSpheres": [],
    }
    cached_payload = await _check_cache_raw(focus_ready)
    assert cached_payload is not None
    assert cached_payload.focus.state == "convergence_today"
    assert cached_payload.focus.content_state == "ready"
    assert [e.id for e in cached_payload.focus.events] == ["ev:1"]
    assert cached_payload.focus.events[0].occurs_at == datetime(2026, 7, 28, 10, 31, 0, tzinfo=UTC)
