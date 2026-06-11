
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_CONTEXT_SERVICE
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Module — apps/api/tests/test_natal_context_service.py
# owns:
#   - apps/api/tests/test_natal_context_service.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# AI_HEADER
# module: M-TEST-NATAL-CONTEXT-SERVICE
# wave: W-NATAL-FULL (Wave 6 — test evidence)
# purpose: Unit tests for NatalContextService — profile_hash, cache hit/miss,
#          invalidation, sidecar validation, no-transit contamination.

import json
import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch, MagicMock

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.db.models import NatalChartCache, UserProfile, User
from app.schemas.natal import NatalContextData, SolarSageNatalResponse
from app.services.natal_context_service import NatalContextService


# ── In-memory DB fixture for these tests ──────────────────────────

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
        first_name="Zhanna",
        gender="female",
        birthday=date(1993, 1, 7),
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


# ── Sidecar mock data ─────────────────────────────────────────────

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
        {"name": "North Node", "longitude": 260.4, "sign": "Sagittarius", "house": 10},
    ],
}


# ══════════════════════════════════════════════════════════════════════
# 1. compute_profile_hash
# ══════════════════════════════════════════════════════════════════════

class TestComputeProfileHash:
    """profile_hash changes when any birth field that affects natal chart changes."""

    def test_hash_is_deterministic(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 == h2, "Same profile must produce same hash"

    def test_hash_changes_on_birthday_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birthday = date(1994, 1, 7)
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when birthday changes"

    def test_hash_changes_on_birth_time_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birth_time = time(14, 0)
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when birth_time changes"

    def test_hash_changes_on_birth_lat_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birth_lat = Decimal("55.75580")
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when birth_lat changes"

    def test_hash_changes_on_birth_lon_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birth_lon = Decimal("37.61730")
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when birth_lon changes"

    def test_hash_changes_on_birth_tz_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birth_tz = "Europe/Moscow"
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when birth_tz changes"

    def test_hash_changes_on_gender_change(self, user_with_profile):
        _, profile = user_with_profile
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.gender = "male"
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when gender changes"

    def test_hash_is_sha256_hex_prefix(self, user_with_profile):
        _, profile = user_with_profile
        h = NatalContextService.compute_profile_hash(profile)
        assert len(h) == 16, "Hash should be 16-char hex prefix"
        assert all(c in "0123456789abcdef" for c in h), "Hash must be hex"


# ══════════════════════════════════════════════════════════════════════
# 2. Cache hit/miss and sidecar call behavior
# ══════════════════════════════════════════════════════════════════════

class TestCacheHitMiss:
    """get_or_build_natal_context must reuse cache on hit, call sidecar on miss."""

    @pytest.mark.asyncio
    async def test_cache_miss_calls_sidecar(self, db: AsyncSession, user_with_profile):
        """First call should call SolarSage sidecar and persist cache."""
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        mock_client.get_natal.assert_called_once()
        assert isinstance(context, NatalContextData)
        assert len(context.planets) > 0

        # Verify cache was persisted
        from sqlalchemy import select
        result = await db.execute(select(NatalChartCache))
        caches = result.scalars().all()
        assert len(caches) == 1

    @pytest.mark.asyncio
    async def test_cache_hit_reuses_without_sidecar(self, db: AsyncSession, user_with_profile):
        """Second call should NOT call sidecar — returns cached context."""
        user, _ = user_with_profile
        service = NatalContextService(db)

        # First call: cache miss
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client
            context1 = await service.get_or_build_natal_context(user.id)

        # Second call: cache hit
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client
            context2 = await service.get_or_build_natal_context(user.id)

        mock_client.get_natal.assert_not_called()
        assert context1.planets[0].name == context2.planets[0].name

    @pytest.mark.asyncio
    async def test_incomplete_profile_raises_409(self, db: AsyncSession, user_with_profile):
        """Profile missing required fields must raise HTTPException 409."""
        user, _ = user_with_profile
        # Remove birth data
        from sqlalchemy import select
        result = await db.execute(
            select(UserProfile).where(UserProfile.user_id == user.id)
        )
        profile = result.scalar_one()
        profile.birth_time = None  # Make incomplete
        await db.commit()

        service = NatalContextService(db)
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            await service.get_or_build_natal_context(user.id)
        assert exc_info.value.status_code == 409


# ══════════════════════════════════════════════════════════════════════
# 3. Invalidation
# ══════════════════════════════════════════════════════════════════════

class TestInvalidation:
    """invalidate_for_user marks active caches as invalidated."""

    @pytest.mark.asyncio
    async def test_invalidate_marks_invalidated_at(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        # Build cache first
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        # Invalidate
        await service.invalidate_for_user(user.id, "test_invalidation")

        from sqlalchemy import select
        result = await db.execute(select(NatalChartCache))
        caches = result.scalars().all()
        assert len(caches) == 1
        assert caches[0].invalidated_at is not None

    @pytest.mark.asyncio
    async def test_invalidated_cache_causes_sidecar_recall(self, db: AsyncSession, user_with_profile):
        """After invalidation, next call should rebuild (call sidecar again)."""
        user, _ = user_with_profile
        service = NatalContextService(db)

        # Build cache
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        # Invalidate
        await service.invalidate_for_user(user.id, "profile_edit")

        # Next call should call sidecar again
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        mock_client.get_natal.assert_called_once()


# ══════════════════════════════════════════════════════════════════════
# 4. Sidecar validation
# ══════════════════════════════════════════════════════════════════════

class TestSidecarValidation:
    """Sidecar response validation — reject empty/broken data."""

    def test_solar_sage_natal_rejects_empty_planets(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="at least one planet"):
            SolarSageNatalResponse(
                house_system="Placidus",
                planets=[],
                houses=[{"number": 1, "longitude": 0.0, "sign": "Aries"}],
            )

    def test_solar_sage_natal_rejects_empty_houses(self):
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="at least one house"):
            SolarSageNatalResponse(
                house_system="Placidus",
                planets=[{"name": "Sun", "longitude": 0.0, "sign": "Aries"}],
                houses=[],
            )

    def test_solar_sage_natal_accepts_valid_response(self):
        resp = SolarSageNatalResponse(
            house_system="Placidus",
            planets=[{"name": "Sun", "longitude": 0.0, "sign": "Aries"}],
            houses=[{"number": 1, "longitude": 0.0, "sign": "Aries"}],
        )
        assert len(resp.planets) == 1
        assert len(resp.houses) == 1

    def test_solar_sage_transits_rejects_empty_planets(self):
        from app.schemas.natal import SolarSageTransitsResponse
        from pydantic import ValidationError
        with pytest.raises(ValidationError, match="at least one planet"):
            SolarSageTransitsResponse(planets=[])

    def test_solar_sage_transits_accepts_valid_response(self):
        from app.schemas.natal import SolarSageTransitsResponse
        resp = SolarSageTransitsResponse(
            planets=[{"name": "Sun", "longitude": 0.0, "sign": "Aries"}],
        )
        assert len(resp.planets) == 1


# ══════════════════════════════════════════════════════════════════════
# 5. No transit contamination in natal context
# ══════════════════════════════════════════════════════════════════════

class TestNoTransitContamination:
    """NatalContextService must NEVER call transits or include transit data."""

    @pytest.mark.asyncio
    async def test_context_service_does_not_call_transits(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        # get_transits should never be called
        mock_client.get_transits.assert_not_called()

    @pytest.mark.asyncio
    async def test_natal_context_has_no_transit_signals(self, db: AsyncSession, user_with_profile):
        """NatalContextData must not contain any Transit_ prefixed planet names."""
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        # No Transit_ in planet names
        for planet in context.planets:
            assert not planet.name.startswith("Transit_"), (
                f"Natal context must not contain transit planet: {planet.name}"
            )

        # No Transit_ in aspect planet_a/planet_b
        for aspect in context.aspects:
            assert not aspect.planet_a.startswith("Transit_"), (
                f"Natal context must not contain transit aspect: {aspect.planet_a}"
            )
            assert not aspect.planet_b.startswith("Transit_"), (
                f"Natal context must not contain transit aspect: {aspect.planet_b}"
            )


# ══════════════════════════════════════════════════════════════════════
# 6. Context data structure
# ══════════════════════════════════════════════════════════════════════

class TestContextDataStructure:
    """Verify NatalContextData contains expected structural elements."""

    @pytest.mark.asyncio
    async def test_context_contains_angles(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        angle_names = {a.name for a in context.angles}
        assert "ASC" in angle_names, "Context must contain ASC angle"
        assert "MC" in angle_names, "Context must contain MC angle"

    @pytest.mark.asyncio
    async def test_context_contains_sphere_scores(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        assert isinstance(context.sphere_scores, dict)
        assert len(context.sphere_scores) > 0, "Context must have sphere scores"

    @pytest.mark.asyncio
    async def test_context_contains_elements_balance(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        # At least one element should be > 0 (we have 7 planets)
        total = (
            context.elements_balance.fire
            + context.elements_balance.earth
            + context.elements_balance.air
            + context.elements_balance.water
        )
        assert total > 0, "Elements balance must reflect actual planets"

    @pytest.mark.asyncio
    async def test_context_contains_dominants(self, db: AsyncSession, user_with_profile):
        user, _ = user_with_profile
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = MOCK_SIDECAR_NATAL
            mock_factory.return_value = mock_client

            context = await service.get_or_build_natal_context(user.id)

        assert len(context.dominants) > 0, "Context must have dominant planets"
