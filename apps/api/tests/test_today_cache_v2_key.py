"""Tests: W5 versioned cache key."""
import uuid
import json
from datetime import date as Date, time as Time
from datetime import datetime, UTC

import pytest
from sqlalchemy import select

from app.services.cache_key_service import build_today_cache_key, expected_cache_identity
from app.db.models import TodayPayloadCache, SemanticLayerCache, User, UserProfile
from app.schemas.today import TodayPayload, TodayMeta, DaySummaryBlock, ConcreteAdviceBlock, ConcreteAdviceCounts
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService, TODAY_CONTENT_VERSION
from app.services.calendar_service import CalendarService
from app.services.cache_key_service import get_canon_versions


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
    assert k.activation_layer_version == "al-1.0"


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
        llm_prompt_version=2,
        frontend_payload_version=1,
    )
    assert k.user_id == uid
    assert k.target_date == "2026-07-08"
    assert k.profile_hash == "abc"
    assert k.calculation_version == "1"
    assert k.activation_layer_version == "al-1.0"
    assert k.scoring_version == 1
    assert k.llm_prompt_version == 2
    assert k.frontend_payload_version == 1


# ── DB-level cache identity ──────────────────────────────────────────────


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
