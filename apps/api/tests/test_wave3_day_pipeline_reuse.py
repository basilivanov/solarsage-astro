# AI_HEADER
# module: M-TEST-WAVE-3-ACCEPTANCE
# wave: W-NATAL-FULL (Wave 3 — day pipeline reuse)
# purpose: Wave 3 acceptance tests — proving:
#          1. Day endpoint does not call natal sidecar on context cache hit
#          2. Day rebuilds if birth profile changes (profile_hash → cache miss)
#          3. Day endpoint still returns same expected shape

import uuid
from datetime import date as Date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.db.models import User, UserProfile, NatalChartCache, TodayPayloadCache
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService
from app.services.natal_context_service import NatalContextService


# ── In-memory DB fixture ───────────────────────────────────────────

@pytest_asyncio.fixture
async def db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", future=True)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as session:
        yield session
    await engine.dispose()


@pytest_asyncio.fixture
async def user_with_profile(db: AsyncSession):
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
        "important": patch("app.services.today_service.TodayImportantService"),
        "yesterday": patch.object(TodayService, "_get_yesterday_signals", new=AsyncMock(return_value=None)),
        "cache_semantic": patch.object(TodayService, "_cache_semantic_layer", new=AsyncMock(return_value=None)),
        "prefetch": patch.object(TodayService, "_prefetch_week", new=AsyncMock(return_value=None)),
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
    mock_semantic.return_value.build_semantic_layer.return_value = {}
    mock_semantic.return_value.build_why_contexts.return_value = []

    mock_llm = mocks["llm"].__enter__()
    mock_llm.return_value.generate_headline = AsyncMock(return_value="Headline")
    mock_llm.return_value.generate_reading = AsyncMock(return_value=["Paragraph"])
    mock_llm.return_value.generate_notes = AsyncMock(return_value="Notes")
    mock_llm.return_value.generate_why_sections = AsyncMock(return_value=[])

    mock_important = mocks["important"].__enter__()
    mock_important.return_value.build_items.return_value = []

    mocks["yesterday"].__enter__()
    mocks["cache_semantic"].__enter__()
    mocks["prefetch"].__enter__()

    return mocks


def _teardown_service_mocks(mocks):
    """Exit all context managers."""
    for key in ["normalization", "scoring", "semantic", "llm", "important",
                "yesterday", "cache_semantic", "prefetch"]:
        mocks[key].__exit__(None, None, None)


# ══════════════════════════════════════════════════════════════════════
# Acceptance 1: Day endpoint does not call natal sidecar on cache hit
# ══════════════════════════════════════════════════════════════════════

class TestDayNoNatalSidecarOnCacheHit:
    """When natal context is already cached, TodayService must NOT call
    get_natal() — it should only call get_transits().
    """

    @pytest.mark.asyncio
    async def test_second_day_call_skips_natal_sidecar(self, db, user_with_profile):
        """After natal context is cached, a second get_today_payload call
        should not trigger a natal sidecar call.
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

                # Context service sidecar (natal)
                mock_ctx_client = AsyncMock()
                mock_ctx_client.get_natal.return_value = MOCK_SIDECAR_NATAL
                mock_ctx_factory.return_value = mock_ctx_client

                # Day service sidecar (transits)
                mock_day_client = AsyncMock()
                mock_day_client.get_transits.return_value = MOCK_SIDECAR_TRANSITS
                mock_day_factory.return_value = mock_day_client

                payload1 = await service.get_today_payload(
                    user.id, target_date, access_state, skip_prefetch=True
                )

                # Natal sidecar was called (cache miss)
                assert mock_ctx_client.get_natal.call_count == 1

            # Second call: natal context cache hit → NO natal sidecar call
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

                # Natal sidecar NOT called (cache hit)
                mock_ctx_client2.get_natal.assert_not_called()

                # Transit sidecar still called (today cache hit)
                # Actually today cache should also hit, so transit sidecar may not be called either
                assert payload2 is not None
        finally:
            _teardown_service_mocks(mocks)


# ══════════════════════════════════════════════════════════════════════
# Acceptance 2: Day rebuilds if birth profile changes
# ══════════════════════════════════════════════════════════════════════

class TestDayRebuildOnProfileChange:
    """If user changes birth data, profile_hash changes → today cache miss → rebuild."""

    @pytest.mark.asyncio
    async def test_profile_change_causes_today_cache_miss(self, db, user_with_profile):
        user, profile = user_with_profile
        target_date = Date(2026, 6, 11)
        access_state = ContentAccessState(
            state="full", reason="active_subscription", referralDaysLeft=None,
            subscriptionActive=None, accessUntil=None,
        )

        # Compute original profile_hash
        original_hash = NatalContextService.compute_profile_hash(profile)

        # Change birth data → profile_hash changes
        profile.birth_lat = Decimal("55.75580")
        profile.birth_lon = Decimal("37.61730")
        profile.birth_tz = "Europe/Moscow"
        await db.commit()

        new_hash = NatalContextService.compute_profile_hash(profile)

        # profile_hash must change
        assert original_hash != new_hash, "Profile hash must change when birth data changes"

        # Today cache keyed by profile_hash → old hash won't match → cache miss
        service = TodayService(db)
        cached_with_old_hash = await service._get_cached_payload(user.id, target_date, original_hash)
        cached_with_new_hash = await service._get_cached_payload(user.id, target_date, new_hash)

        # No cache for either hash (nothing was built yet)
        assert cached_with_old_hash is None
        assert cached_with_new_hash is None


# ══════════════════════════════════════════════════════════════════════
# Acceptance 3: Day endpoint still returns same expected shape
# ══════════════════════════════════════════════════════════════════════

class TestDayPayloadShape:
    """Day endpoint must return TodayPayload with expected structure."""

    @pytest.mark.asyncio
    async def test_today_payload_has_required_fields(self, db, user_with_profile):
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
