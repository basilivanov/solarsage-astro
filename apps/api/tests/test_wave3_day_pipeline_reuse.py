# ############################################################################
# AI_HEADER: M-TEST-WAVE3-DAY-PIPELINE-REUSE — Wave 3 acceptance tests.
# ROLE: Proves day endpoint reuses natal context, rebuilds on profile change,
#       and returns expected shape.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-WAVE3-DAY-PIPELINE-REUSE
# purpose: Verify day endpoint natal-context cache hit, profile-change rebuild,
#          and payload shape invariants.
# owns:
#   - apps/api/tests/test_wave3_day_pipeline_reuse.py
# inputs: In-memory DB fixtures, service mocks, sidecar doubles.
# outputs: Assertion evidence for natal-cache, rebuild, and shape proofs.
# dependencies: test fixtures, app models/services, mock sidecar data.
# side_effects: In-memory DB reads/writes via fixtures.
# emitted_logs: none.
# invariants: none.
# failure_policy: AssertionError on test failure.
# END_MODULE_CONTRACT: M-TEST-WAVE3-DAY-PIPELINE-REUSE

# START_MODULE_MAP: M-TEST-WAVE3-DAY-PIPELINE-REUSE
# public_entrypoints:
#   - db
#   - user_with_profile
#   - test_same_date_both_caches_hit
#   - test_different_date_today_miss_natal_hit
#   - test_profile_change_causes_today_cache_miss
#   - test_rebuild_after_profile_change_end_to_end
#   - test_today_payload_has_required_fields
#   - test_day_client_does_not_call_get_natal
# owned_tests:
#   - apps/api/tests/test_wave3_day_pipeline_reuse.py
# END_MODULE_MAP: M-TEST-WAVE3-DAY-PIPELINE-REUSE

import uuid
from datetime import date as Date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.db.models import User, UserProfile
from app.schemas.access import ContentAccessState
from app.schemas.semantic import SemanticLayer
from app.services.today_service import TodayService
from app.services.natal_context_service import NatalContextService


# ── In-memory DB fixture ───────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.db
    # purpose: Provide a fresh in-memory SQLite session per test.
    # inputs: none.
    # returns: AsyncSession (yielded) bound to an ephemeral in-memory SQLite.
    # side_effects: Creates schema on setup, disposes engine on teardown.
    # emitted_logs: none.
    # error_behavior: Raises on DB create/fixture failure.
    # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.db
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def user_with_profile(db: AsyncSession):
    # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.user_with_profile
    # purpose: Create a basic User + UserProfile with complete birth data.
    # inputs: db — AsyncSession from the db fixture.
    # returns: tuple[User, UserProfile] (yielded) with real UUID, tg_user_id, and birth coordinates.
    # side_effects: Commits User and UserProfile to the DB.
    # emitted_logs: none.
    # error_behavior: Raises on commit failure.
    # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.user_with_profile
    """Create a User + UserProfile with complete birth data."""
    user_id = uuid.uuid4()
    user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
    db.add(user)
    await db.commit()

    profile = UserProfile(
        user_id=user_id,
        first_name="Test",
        gender="female",
        birthday=Date(1993, 1, 7),
        birth_time=time(10, 33),
        birth_city="Chirchiq",
        birth_lat=Decimal("41.46890"),
        birth_lon=Decimal("69.58220"),
        birth_tz="Asia/Tashkent",
        is_onboarded=True,
    )
    db.add(profile)
    await db.commit()
    return user, profile


MOCK_SIDECAR_NATAL = {
    "house_system": "Placidus",
    "planets": [
        {"name": "Sun", "longitude": 286.93, "sign": "Capricorn", "house": 11, "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 119.63, "sign": "Gemini", "house": 4, "retrograde": False, "speed": 1.0},
        {"name": "Mercury", "longitude": 277.10, "sign": "Capricorn", "house": 10, "retrograde": False, "speed": 1.0},
        {"name": "Venus", "longitude": 333.55, "sign": "Pisces", "house": 12, "retrograde": False, "speed": 1.0},
        {"name": "Mars", "longitude": 137.95, "sign": "Cancer", "house": 5, "retrograde": True, "speed": -0.5},
        {"name": "Jupiter", "longitude": 193.95, "sign": "Libra", "house": 7, "retrograde": False, "speed": 0.2},
        {"name": "Saturn", "longitude": 327.02, "sign": "Aquarius", "house": 12, "retrograde": False, "speed": 0.1},
    ],
    "houses": [
        {"number": i, "longitude": float((i - 1) * 30), "sign": "Aries" if i == 1 else "Taurus"}
        for i in range(1, 13)
    ],
    "special_points": [
        {"name": "ASC", "longitude": 341.9, "sign": "Pisces", "house": None},
        {"name": "MC", "longitude": 260.5, "sign": "Sagittarius", "house": None},
    ],
}

MOCK_SIDECAR_TRANSITS = {
    "planets": [
        {"name": "Sun", "longitude": 80.0, "sign": "Gemini", "retrograde": False, "speed": 1.0},
        {"name": "Moon", "longitude": 200.0, "sign": "Libra", "retrograde": False, "speed": 1.0},
    ],
}


def _mock_all_services():
    """Return a dict of context managers that mock all services except sidecar + NatalContextService."""
    return {
        "normalization": patch("app.services.today_service.NormalizationService"),
        "scoring": patch("app.services.today_service.ScoringService"),
        "semantic": patch("app.services.today_service.SemanticService"),
        "llm": patch("app.services.today_service.LLMService"),
        # The interpretation service has its own LLMService reference; the
        # concrete-advice batch must be a valid 12-key payload so the built
        # payload stays cacheable (a degraded all-fallback advice batch is
        # never written to the TodayPayload cache by contract).
        "llm_interpretation": patch("app.services.today_interpretation_service.LLMService"),
        "llm_key": patch("app.core.config.settings.openrouter_api_key", "test-wave3-key"),
        "important": patch("app.services.today_service.TodayImportantService"),
        "yesterday": patch.object(TodayService, "_get_yesterday_signals", new=AsyncMock(return_value=None)),
        "cache_semantic": patch.object(TodayService, "_cache_semantic_layer", new=AsyncMock(return_value=None)),
    }


def _setup_service_mocks(mocks):
    """Configure all service mocks to return valid data."""
    mock_normalization = mocks["normalization"].__enter__()
    mock_normalization.return_value.normalize_day.return_value = []

    mock_scoring = mocks["scoring"].__enter__()
    mock_scoring.return_value.score_day.return_value = {
        "day_status": "steady",
        "sphere_scores": {},
        "top_signals": [],
    }

    mock_semantic = mocks["semantic"].__enter__()
    mock_semantic.return_value.build_semantic_layer.return_value = SemanticLayer(
        day_status="steady",
        day_theme="Спокойный день",
        sphere_themes=[],
        top_keywords=[],
    )
    mock_semantic.return_value.build_why_contexts.return_value = []

    mock_llm = mocks["llm"].__enter__()
    mock_llm.return_value.generate_headline = AsyncMock(return_value="Headline")
    mock_llm.return_value.generate_reading = AsyncMock(return_value=["Paragraph"])
    mock_llm.return_value.generate_notes = AsyncMock(return_value="Notes")
    mock_llm.return_value.generate_why_sections = AsyncMock(return_value=[])

    mock_llm_interpretation = mocks["llm_interpretation"].__enter__()
    mock_llm_interpretation.return_value.generate_concrete_advice = AsyncMock(return_value={
        k: f"Спокойный день для дела номер {i}."
        for i, k in enumerate([
            "work", "money", "documents", "relationships", "sport", "communication",
            "health", "decisions", "travel", "creativity", "study", "shopping",
        ])
    })
    mock_llm_interpretation.return_value.generate_planet_interpretations = AsyncMock(return_value=None)
    mocks["llm_key"].__enter__()

    mock_important = mocks["important"].__enter__()
    mock_important.return_value.build_items.return_value = []

    mocks["yesterday"].__enter__()
    mocks["cache_semantic"].__enter__()

    return mocks


def _teardown_service_mocks(mocks):
    """Exit all context managers."""
    for key in ["normalization", "scoring", "semantic", "llm", "llm_interpretation",
                "llm_key", "important", "yesterday", "cache_semantic"]:
        mocks[key].__exit__(None, None, None)


# ══════════════════════════════════════════════════════════════════════
# Acceptance 1: Day endpoint does not call natal sidecar on cache hit
# ══════════════════════════════════════════════════════════════════════

class TestDayNoNatalSidecarOnCacheHit:
    """When natal context is already cached, TodayService must NOT call
    get_natal() — it should only call get_transits().
    """

    @pytest.mark.asyncio
    async def test_same_date_both_caches_hit(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayNoNatalSidecarOnCacheHit.test_same_date_both_caches_hit
        # purpose: Second call for same date hits both caches — no sidecar calls.
        # inputs: db, user_with_profile from fixtures; mocks all external services.
        # returns: none — assertions only.
        # side_effects: Reads/writes TodayPayloadCache and NatalChartCache rows.
        # error_behavior: Assertion failure on cache hit/miss or sidecar call count.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayNoNatalSidecarOnCacheHit.test_same_date_both_caches_hit
        """After building a payload for a date, a second call for the same date
        hits both TodayPayload cache and NatalContext cache — no sidecar calls at all.
        """
        user, profile = user_with_profile
        target_date = Date(2026, 6, 11)
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        service = TodayService(db)
        mocks = _mock_all_services()
        _setup_service_mocks(mocks)

        try:
            # First call: natal context miss → sidecar call
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory:

                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                payload1 = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # Natal sidecar was called (cache miss)
                assert mock_ctx_client.get_natal.call_count == 1
                assert payload1.meta.cached is False

            # Second call (same date): TodayPayload cache hit → NO sidecar calls
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory2, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory2:

                mock_ctx_client2 = AsyncMock()
                mock_ctx_client2.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory2.return_value = mock_ctx_client2

                mock_day_client2 = AsyncMock()
                mock_day_client2.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory2.return_value = mock_day_client2

                payload2 = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # Both sidecars NOT called (TodayPayload cache hit)
                mock_ctx_client2.get_natal.assert_not_called()
                mock_day_client2.get_transits.assert_not_called()
                assert payload2.meta.cached is True
        finally:
            _teardown_service_mocks(mocks)

    @pytest.mark.asyncio
    async def test_different_date_today_miss_natal_hit(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayNoNatalSidecarOnCacheHit.test_different_date_today_miss_natal_hit
        # purpose: Different date → TodayPayload miss, NatalContext hit → no natal sidecar call, transit sidecar called.
        # inputs: db, user_with_profile from fixtures.
        # returns: none — assertions only.
        # side_effects: Two payload builds for date_a and date_b; cache reads/writes.
        # error_behavior: Assertion failure on cache behavior or meta.cached flag.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayNoNatalSidecarOnCacheHit.test_different_date_today_miss_natal_hit
        """Key scenario: call for date A caches natal context. Then call for
        date B: TodayPayload cache MISSES (different date), but NatalContext
        cache HITS (same user). Proves:
        - natal sidecar NOT called (NatalContext cache hit)
        - transit sidecar IS called (need transits for new date)
        - fresh TodayPayload generated with meta.cached=False
        """
        user, profile = user_with_profile
        date_a = Date(2026, 6, 11)
        date_b = Date(2026, 6, 12)  # different date → TodayPayload miss
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        service = TodayService(db)
        mocks = _mock_all_services()
        _setup_service_mocks(mocks)

        try:
            # Call 1: date A → natal context miss, sidecar called
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory:

                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                payload_a = await service.get_today_payload(
                    user.id, date_a, access_state, skip_prefetch=True
                )

                # Both sidecars called (fresh generation)
                assert mock_ctx_client.get_natal.call_count == 1
                assert mock_day_client.get_transits.call_count == 1
                assert payload_a.meta.cached is False

            # Call 2: date B → TodayPayload miss, NatalContext hit
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory2, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory2:

                mock_ctx_client2 = AsyncMock()
                mock_ctx_client2.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory2.return_value = mock_ctx_client2

                mock_day_client2 = AsyncMock()
                mock_day_client2.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory2.return_value = mock_day_client2

                payload_b = await service.get_today_payload(
                    user.id, date_b, access_state, skip_prefetch=True
                )

                # Natal sidecar NOT called (NatalContext cache hit)
                mock_ctx_client2.get_natal.assert_not_called()

                # Transit sidecar IS called (different date, need fresh transits)
                assert mock_day_client2.get_transits.call_count == 1

                # Fresh TodayPayload (not from cache)
                assert payload_b.meta.cached is False
                assert payload_b.date == date_b.isoformat()
        finally:
            _teardown_service_mocks(mocks)


# ══════════════════════════════════════════════════════════════════════
# Acceptance 2: Day rebuilds if birth profile changes
# ══════════════════════════════════════════════════════════════════════

class TestDayRebuildOnProfileChange:
    """If user changes birth data, profile_hash changes → today cache miss → rebuild."""

    @pytest.mark.asyncio
    async def test_profile_change_causes_today_cache_miss(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayRebuildOnProfileChange.test_profile_change_causes_today_cache_miss
        # purpose: Verify profile_hash changes when birth data is modified.
        # inputs: db, user_with_profile from fixtures.
        # returns: none — assertions only.
        # side_effects: Modifies profile birth coordinates and commits.
        # error_behavior: Assertion failure if hash does not change.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayRebuildOnProfileChange.test_profile_change_causes_today_cache_miss
        """Baseline: verify that profile_hash changes when birth data changes."""
        user, profile = user_with_profile
        original_hash = NatalContextService.compute_profile_hash(profile)

        # Change birth data → profile_hash changes
        profile.birth_lat = Decimal("55.75580")
        profile.birth_lon = Decimal("37.61730")
        profile.birth_tz = "Europe/Moscow"
        await db.commit()

        new_hash = NatalContextService.compute_profile_hash(profile)
        assert original_hash != new_hash, "Profile hash must change when birth data changes"

    @pytest.mark.asyncio
    async def test_rebuild_after_profile_change_end_to_end(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayRebuildOnProfileChange.test_rebuild_after_profile_change_end_to_end
        # purpose: Full end-to-end: build, change profile, rebuild — verifies natal sidecar is called again and meta.cached=False.
        # inputs: db, user_with_profile from fixtures.
        # returns: none — assertions only.
        # side_effects: Two payload builds, profile modification, cache round-trips.
        # error_behavior: Assertion failure on cache behavior, sidecar calls, or meta flags.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayRebuildOnProfileChange.test_rebuild_after_profile_change_end_to_end
        """Full end-to-end scenario:
        1. Build payload with original birth data → cached with original profile_hash
        2. Change birth data → new profile_hash → old cache becomes stale
        3. Call get_today_payload again → proves rebuild:
           - natal sidecar called again (new context)
           - meta.cached=False (fresh generation)
           - new cache entry with new profile_hash exists
           - old cache entry with old profile_hash still exists but is not returned
        """
        user, profile = user_with_profile
        target_date = Date(2026, 6, 11)
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        service = TodayService(db)
        mocks = _mock_all_services()
        _setup_service_mocks(mocks)

        original_hash = NatalContextService.compute_profile_hash(profile)

        try:
            # Step 1: Build payload with original birth data
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory:

                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                payload1 = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # First call: natal sidecar called (cache miss)
                assert mock_ctx_client.get_natal.call_count == 1
                assert payload1.meta.cached is False

            # Verify old cache exists
            cached_old = await service._get_cached_payload(user.id, target_date, original_hash)
            assert cached_old is not None, "Payload should be cached with original profile_hash"

            # Step 2: Change birth data
            profile.birth_lat = Decimal("55.75580")
            profile.birth_lon = Decimal("37.61730")
            profile.birth_tz = "Europe/Moscow"
            await db.commit()

            new_hash = NatalContextService.compute_profile_hash(profile)
            assert original_hash != new_hash, "Profile hash must change"

            # Old hash cache still exists but new hash cache doesn't
            cached_old_still = await service._get_cached_payload(user.id, target_date, original_hash)
            assert cached_old_still is not None, "Old cache entry persists in DB"
            cached_new = await service._get_cached_payload(user.id, target_date, new_hash)
            assert cached_new is None, "No cache for new profile_hash yet"

            # Step 3: Call get_today_payload again with new birth data
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory2, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory2:

                mock_ctx_client2 = AsyncMock()
                mock_ctx_client2.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory2.return_value = mock_ctx_client2

                mock_day_client2 = AsyncMock()
                mock_day_client2.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory2.return_value = mock_day_client2

                payload2 = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # Natal sidecar called again (new profile_hash → natal context miss)
                assert mock_ctx_client2.get_natal.call_count == 1

                # Fresh generation, not from cache
                assert payload2.meta.cached is False

            # Verify new cache exists with new profile_hash
            cached_after_rebuild = await service._get_cached_payload(user.id, target_date, new_hash)
            assert cached_after_rebuild is not None, "New payload cached with new profile_hash"

            # Old cache entry still in DB but won't be served (different hash)
            cached_old_after = await service._get_cached_payload(user.id, target_date, original_hash)
            assert cached_old_after is not None, "Old cache entry still in DB (not deleted, just not matched)"
        finally:
            _teardown_service_mocks(mocks)


# ══════════════════════════════════════════════════════════════════════
# Acceptance 3: Day endpoint still returns same expected shape
# ══════════════════════════════════════════════════════════════════════

class TestDayPayloadShape:
    """Day endpoint must return TodayPayload with expected structure."""

    @pytest.mark.asyncio
    async def test_today_payload_has_required_fields(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayPayloadShape.test_today_payload_has_required_fields
        # purpose: Verify TodayPayload response contains all required structural fields.
        # inputs: db, user_with_profile from fixtures; mocks external services.
        # returns: none — assertions only.
        # side_effects: Builds a payload via TodayService.
        # error_behavior: Assertion failure on missing or malformed fields.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestDayPayloadShape.test_today_payload_has_required_fields
        user, profile = user_with_profile
        target_date = Date(2026, 6, 11)
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        service = TodayService(db)
        mocks = _mock_all_services()
        _setup_service_mocks(mocks)

        try:
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory:

                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                payload = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

            # Verify TodayPayload shape
            assert payload.meta.schema_version == "today/v1"
            assert payload.meta.cached is False  # Fresh generation
            assert payload.date == target_date.isoformat()
            assert payload.headline == "Headline"
            assert payload.day_status == "steady"
            assert payload.reading is not None
            assert payload.week_strip is not None
            assert len(payload.week_strip) == 7
        finally:
            _teardown_service_mocks(mocks)


# ══════════════════════════════════════════════════════════════════════
# Additional: TodayService never calls get_natal directly
# ══════════════════════════════════════════════════════════════════════

class TestTodayServiceNoDirectNatalCall:
    """TodayService.get_today_payload must NOT call get_natal() on the
    solarsage_client. It must delegate natal facts to NatalContextService.
    """

    @pytest.mark.asyncio
    async def test_day_client_does_not_call_get_natal(self, db, user_with_profile):
        # START_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestTodayServiceNoDirectNatalCall.test_day_client_does_not_call_get_natal
        # purpose: Prove TodayService uses sidecar client only for get_transits(), never get_natal().
        # inputs: db, user_with_profile from fixtures; mocks external services.
        # returns: none — assertions only.
        # side_effects: Builds a payload via TodayService with spy on sidecar client.
        # error_behavior: Assertion failure if get_natal is called.
        # emitted_logs: none.
        # END_FUNCTION_CONTRACT: F-M-TEST-WAVE3-DAY-PIPELINE-REUSE.TestTodayServiceNoDirectNatalCall.test_day_client_does_not_call_get_natal
        """The sidecar client obtained in TodayService must only call get_transits()."""
        user, profile = user_with_profile
        target_date = Date(2026, 6, 11)
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        service = TodayService(db)
        mocks = _mock_all_services()
        _setup_service_mocks(mocks)

        try:
            with patch("app.services.natal_context_service.get_solarsage_client") as mock_ctx_factory, \
                 patch("app.services.today_service.get_solarsage_client") as mock_day_factory:

                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # The day service client must NOT call get_natal()
                mock_day_client.get_natal.assert_not_called()

                # The day service client SHOULD call get_transits()
                mock_day_client.get_transits.assert_called()
        finally:
            _teardown_service_mocks(mocks)
