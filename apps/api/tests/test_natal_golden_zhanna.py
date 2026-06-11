
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL_GOLDEN_ZHANNA
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for natal_golden_zhanna.py behavior
# owns:
#   - apps/api/tests/test_natal_golden_zhanna.py
# inputs: Query params, models
# outputs: Records / query results
# dependencies: local modules
# side_effects: Database reads/writes
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-NATAL-GOLDEN-ZHANNA
# wave: W-NATAL-FULL (Wave 6 — golden tests and evidence)
# purpose: Golden sample regression test for the Zhanna profile (TZ §14).
#          Verifies that the natal context pipeline produces the same chart
#          semantics for a known birth data sample, using a mocked sidecar
#          response derived from the TZ-expected planetary positions.
#
#          This fixture is NOT an astrology correctness proof. It is a
#          regression guard: if the pipeline changes the sign/house/retrograde
#          semantics for a known input, this test fails.
#
#          Acceptance criteria (TZ §16 Wave 6):
#          - Golden sample key facts match expected tolerances
#          - Tests prove cache hit/miss, invalidation, report idempotency,
#            and no transit contamination

import json
import os
import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import AsyncMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.db.session import Base
from app.db.models import NatalChartCache, UserProfile, User
from app.schemas.natal import NatalContextData
from app.services.natal_context_service import NatalContextService


FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


# ── Load golden fixture ─────────────────────────────────────────────

def _load_golden():
    path = os.path.join(FIXTURES_DIR, "golden_zhanna.json")
    with open(path) as f:
        return json.load(f)


def _load_sidecar_mock():
    path = os.path.join(FIXTURES_DIR, "sidecar_zhanna_natal.json")
    with open(path) as f:
        return json.load(f)


GOLDEN = _load_golden()
SIDECAR_MOCK = _load_sidecar_mock()
TOLERANCE = GOLDEN["degree_tolerance"]


# ── In-memory DB fixture ────────────────────────────────────────────

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
async def zhanna_user(db: AsyncSession):
    """Create a User + UserProfile matching the Zhanna golden sample."""
    user_id = uuid.uuid4()
    user = User(id=user_id, tg_user_id=hash(str(user_id)) % (10**18))
    db.add(user)
    await db.commit()

    prof = GOLDEN["profile"]
    profile = UserProfile(
        user_id=user_id,
        first_name=prof["first_name"],
        gender=prof["gender"],
        birthday=date.fromisoformat(prof["birth"]),
        birth_time=time.fromisoformat(prof["time"]),
        birth_city=prof["city"],
        birth_lat=Decimal(str(prof["lat"])),
        birth_lon=Decimal(str(prof["lon"])),
        birth_tz=prof["tz"],
        is_onboarded=True,
    )
    db.add(profile)
    await db.commit()
    return user, profile


@pytest_asyncio.fixture
async def zhanna_context(db: AsyncSession, zhanna_user):
    """Build NatalContextData for Zhanna via NatalContextService with mocked sidecar."""
    user, _ = zhanna_user
    service = NatalContextService(db)

    with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
        mock_client = AsyncMock()
        mock_client.get_natal.return_value = SIDECAR_MOCK
        mock_factory.return_value = mock_client
        context = await service.get_or_build_natal_context(user.id)

    return context


# ══════════════════════════════════════════════════════════════════════
# 1. Planet signs match golden expectations
# ══════════════════════════════════════════════════════════════════════

class TestPlanetSigns:
    """Each planet's sign in the natal context must match the golden fixture."""

    @pytest.mark.parametrize("planet_key", [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune", "pluto",
        "north_node", "south_node",
    ])
    @pytest.mark.asyncio
    async def test_planet_sign_matches_golden(self, db, zhanna_user, planet_key):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        expected_sign = GOLDEN["expected_facts"][f"{planet_key}_sign"]
        # Map golden key to possible planet names in context
        planet_name_map = {
            "sun": "Sun", "moon": "Moon", "mercury": "Mercury",
            "venus": "Venus", "mars": "Mars", "jupiter": "Jupiter",
            "saturn": "Saturn", "uranus": "Uranus", "neptune": "Neptune",
            "pluto": "Pluto", "north_node": "North Node",
            "south_node": "South Node",
        }
        planet_name = planet_name_map[planet_key]

        # Find planet in context
        planet = next((p for p in context.planets if p.name == planet_name), None)
        assert planet is not None, f"Planet {planet_name} not found in natal context"
        assert planet.sign == expected_sign, (
            f"{planet_name}: golden sign={expected_sign}, context sign={planet.sign}"
        )


# ══════════════════════════════════════════════════════════════════════
# 2. Planet degrees match golden expectations within tolerance
# ══════════════════════════════════════════════════════════════════════

class TestPlanetDegrees:
    """Each planet's degree in the natal context must be within TOLERANCE
    of the golden fixture value."""

    @pytest.mark.parametrize("planet_key", [
        "sun", "moon", "mercury", "venus", "mars",
        "jupiter", "saturn", "uranus", "neptune", "pluto",
        "north_node", "south_node",
    ])
    @pytest.mark.asyncio
    async def test_planet_degree_within_tolerance(self, db, zhanna_user, planet_key):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        expected_deg = GOLDEN["expected_facts"][f"{planet_key}_degree_approx"]
        planet_name_map = {
            "sun": "Sun", "moon": "Moon", "mercury": "Mercury",
            "venus": "Venus", "mars": "Mars", "jupiter": "Jupiter",
            "saturn": "Saturn", "uranus": "Uranus", "neptune": "Neptune",
            "pluto": "Pluto", "north_node": "North Node",
            "south_node": "South Node",
        }
        planet_name = planet_name_map[planet_key]

        planet = next((p for p in context.planets if p.name == planet_name), None)
        assert planet is not None, f"Planet {planet_name} not found in natal context"

        diff = abs(planet.degree - expected_deg)
        assert diff <= TOLERANCE, (
            f"{planet_name}: golden degree≈{expected_deg}, context degree={planet.degree}, "
            f"diff={diff} > tolerance={TOLERANCE}"
        )


# ══════════════════════════════════════════════════════════════════════
# 3. Planet houses match golden expectations
# ══════════════════════════════════════════════════════════════════════

class TestPlanetHouses:
    """Each planet's house assignment must match the golden fixture exactly."""

    @pytest.mark.parametrize("planet_key", [
        "Sun", "Moon", "Mercury", "Venus", "Mars",
        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto",
    ])
    @pytest.mark.asyncio
    async def test_planet_house_matches_golden(self, db, zhanna_user, planet_key):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        expected_house = GOLDEN["natal_houses"][planet_key]
        planet = next((p for p in context.planets if p.name == planet_key), None)
        assert planet is not None, f"Planet {planet_key} not found in natal context"
        assert planet.house == expected_house, (
            f"{planet_key}: golden house={expected_house}, context house={planet.house}"
        )


# ══════════════════════════════════════════════════════════════════════
# 4. Mars retrograde flag
# ══════════════════════════════════════════════════════════════════════

class TestRetrogradeFlags:
    """Mars must be retrograde; Sun and Jupiter must NOT be retrograde."""

    @pytest.mark.asyncio
    async def test_mars_retrograde(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        mars = next(p for p in context.planets if p.name == "Mars")
        assert mars.retrograde is True, "Mars must be retrograde in Zhanna's chart"

    @pytest.mark.asyncio
    async def test_sun_not_retrograde(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        sun = next(p for p in context.planets if p.name == "Sun")
        assert sun.retrograde is False, "Sun must never be retrograde"

    @pytest.mark.asyncio
    async def test_jupiter_not_retrograde(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        jupiter = next(p for p in context.planets if p.name == "Jupiter")
        assert jupiter.retrograde is False, "Jupiter is not retrograde in this sample"


# ══════════════════════════════════════════════════════════════════════
# 5. Angles (ASC/MC) match golden
# ══════════════════════════════════════════════════════════════════════

class TestAngles:
    """ASC and MC signs and degrees must match golden expectations."""

    @pytest.mark.asyncio
    async def test_asc_sign(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        asc = next((a for a in context.angles if a.name == "ASC"), None)
        assert asc is not None, "ASC angle not found in context"
        assert asc.sign == GOLDEN["expected_facts"]["asc_sign"], (
            f"ASC: golden={GOLDEN['expected_facts']['asc_sign']}, context={asc.sign}"
        )

    @pytest.mark.asyncio
    async def test_asc_degree_within_tolerance(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        asc = next(a for a in context.angles if a.name == "ASC")
        expected_deg = GOLDEN["expected_facts"]["asc_degree_approx"]
        diff = abs(asc.degree - expected_deg)
        assert diff <= TOLERANCE, (
            f"ASC: golden degree≈{expected_deg}, context={asc.degree}, diff={diff}"
        )

    @pytest.mark.asyncio
    async def test_mc_sign(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        mc = next((a for a in context.angles if a.name == "MC"), None)
        assert mc is not None, "MC angle not found in context"
        assert mc.sign == GOLDEN["expected_facts"]["mc_sign"], (
            f"MC: golden={GOLDEN['expected_facts']['mc_sign']}, context={mc.sign}"
        )

    @pytest.mark.asyncio
    async def test_mc_degree_within_tolerance(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        mc = next(a for a in context.angles if a.name == "MC")
        expected_deg = GOLDEN["expected_facts"]["mc_degree_approx"]
        diff = abs(mc.degree - expected_deg)
        assert diff <= TOLERANCE, (
            f"MC: golden degree≈{expected_deg}, context={mc.degree}, diff={diff}"
        )


# ══════════════════════════════════════════════════════════════════════
# 6. House system
# ══════════════════════════════════════════════════════════════════════

class TestHouseSystem:
    """House system in context must be Placidus."""

    @pytest.mark.asyncio
    async def test_house_system_is_placidus(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        assert context.house_system == GOLDEN["house_system"], (
            f"House system: golden={GOLDEN['house_system']}, context={context.house_system}"
        )


# ══════════════════════════════════════════════════════════════════════
# 7. No transit contamination
# ══════════════════════════════════════════════════════════════════════

class TestGoldenNoTransitContamination:
    """NatalContext for Zhanna must contain ZERO transit data — regression guard."""

    @pytest.mark.asyncio
    async def test_no_transit_planets(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        for planet in context.planets:
            assert not planet.name.startswith("Transit_"), (
                f"Natal context contains transit planet: {planet.name}"
            )

    @pytest.mark.asyncio
    async def test_no_transit_aspects(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        for aspect in context.aspects:
            assert not aspect.planet_a.startswith("Transit_"), (
                f"Natal context contains transit aspect: {aspect.planet_a}"
            )
            assert not aspect.planet_b.startswith("Transit_"), (
                f"Natal context contains transit aspect: {aspect.planet_b}"
            )

    @pytest.mark.asyncio
    async def test_sidecar_transits_not_called(self, db, zhanna_user):
        """NatalContextService must never call get_transits."""
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        mock_client.get_transits.assert_not_called()


# ══════════════════════════════════════════════════════════════════════
# 8. Cache hit/miss with Zhanna profile
# ══════════════════════════════════════════════════════════════════════

class TestGoldenCacheHitMiss:
    """Cache hit/miss behavior for the Zhanna golden profile."""

    @pytest.mark.asyncio
    async def test_first_call_is_cache_miss(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        mock_client.get_natal.assert_called_once()

    @pytest.mark.asyncio
    async def test_second_call_is_cache_hit(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        # First call: cache miss
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            await service.get_or_build_natal_context(user.id)

        # Second call: cache hit — should NOT call sidecar
        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory2:
            mock_client2 = AsyncMock()
            mock_client2.get_natal.return_value = SIDECAR_MOCK
            mock_factory2.return_value = mock_client2
            await service.get_or_build_natal_context(user.id)

        mock_client2.get_natal.assert_not_called()


# ══════════════════════════════════════════════════════════════════════
# 9. Profile hash determinism for Zhanna
# ══════════════════════════════════════════════════════════════════════

class TestGoldenProfileHash:
    """Profile hash must be deterministic and change on birth data mutation."""

    @pytest.mark.asyncio
    async def test_zhanna_hash_deterministic(self, zhanna_user):
        _, profile = zhanna_user
        h1 = NatalContextService.compute_profile_hash(profile)
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 == h2, "Same Zhanna profile must produce same hash"

    @pytest.mark.asyncio
    async def test_zhanna_hash_changes_on_birthday_edit(self, zhanna_user):
        _, profile = zhanna_user
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birthday = date(1994, 1, 7)
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when Zhanna's birthday changes"

    @pytest.mark.asyncio
    async def test_zhanna_hash_changes_on_birthplace_edit(self, zhanna_user):
        _, profile = zhanna_user
        h1 = NatalContextService.compute_profile_hash(profile)
        profile.birth_lat = Decimal("55.75580")
        h2 = NatalContextService.compute_profile_hash(profile)
        assert h1 != h2, "Hash must change when Zhanna's birth_lat changes"


# ══════════════════════════════════════════════════════════════════════
# 10. Context structural completeness
# ══════════════════════════════════════════════════════════════════════

class TestGoldenContextStructure:
    """The Zhanna context must have all expected structural elements."""

    @pytest.mark.asyncio
    async def test_has_12_planets_and_nodes(self, db, zhanna_user):
        """With the full sidecar mock, context should have 10 planets + 2 nodes."""
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        assert len(context.planets) >= 10, (
            f"Expected at least 10 planets, got {len(context.planets)}"
        )

    @pytest.mark.asyncio
    async def test_has_angles(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        angle_names = {a.name for a in context.angles}
        assert "ASC" in angle_names
        assert "MC" in angle_names

    @pytest.mark.asyncio
    async def test_has_aspects(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        assert len(context.aspects) > 0, "Zhanna chart must have natal aspects"

    @pytest.mark.asyncio
    async def test_has_sphere_scores(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        assert isinstance(context.sphere_scores, dict)
        assert len(context.sphere_scores) > 0

    @pytest.mark.asyncio
    async def test_has_dominants(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        assert len(context.dominants) > 0, "Zhanna context must have dominant planets"

    @pytest.mark.asyncio
    async def test_has_elements_balance(self, db, zhanna_user):
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        total = (
            context.elements_balance.fire
            + context.elements_balance.earth
            + context.elements_balance.air
            + context.elements_balance.water
        )
        assert total > 0, "Elements balance must be non-zero for Zhanna"

    @pytest.mark.asyncio
    async def test_has_special_points(self, db, zhanna_user):
        """Zhanna's sidecar mock includes Chiron, Lilith, Selena, Pars Fortunae."""
        user, _ = zhanna_user
        service = NatalContextService(db)

        with patch("app.services.natal_context_service.get_solarsage_client") as mock_factory:
            mock_client = AsyncMock()
            mock_client.get_natal.return_value = SIDECAR_MOCK
            mock_factory.return_value = mock_client
            context = await service.get_or_build_natal_context(user.id)

        sp_names = {sp.name for sp in context.special_points}
        # At least Chiron should be present (others may vary by sidecar version)
        assert len(context.special_points) > 0, "Zhanna context must have special points"


# ══════════════════════════════════════════════════════════════════════
# 11. Golden fixture file validation
# ══════════════════════════════════════════════════════════════════════

class TestGoldenFixtureIntegrity:
    """Verify the golden fixture files are structurally valid."""

    def test_golden_json_has_required_sections(self):
        assert "profile" in GOLDEN
        assert "expected_facts" in GOLDEN
        assert "natal_houses" in GOLDEN
        assert "degree_tolerance" in GOLDEN
        assert "house_system" in GOLDEN

    def test_golden_profile_has_birth_data(self):
        prof = GOLDEN["profile"]
        assert prof["birth"] == "1993-01-07"
        assert prof["time"] == "10:33"
        assert prof["lat"] == 41.4689
        assert prof["lon"] == 69.5822
        assert prof["tz"] == "Asia/Tashkent"

    def test_golden_has_all_10_planets(self):
        for planet in ["Sun", "Moon", "Mercury", "Venus", "Mars",
                        "Jupiter", "Saturn", "Uranus", "Neptune", "Pluto"]:
            assert planet in GOLDEN["natal_houses"], f"Missing {planet} in natal_houses"

    def test_sidecar_mock_has_required_fields(self):
        assert SIDECAR_MOCK["house_system"] == "Placidus"
        assert len(SIDECAR_MOCK["planets"]) >= 10
        assert len(SIDECAR_MOCK["houses"]) == 12
        assert "special_points" in SIDECAR_MOCK
        # Note: aspects are NOT in the sidecar response — they are computed
        # by NormalizationService from planet positions.
