"""Tests for TodayMeta versioning fields — W1 versioning skeleton + W2 behavioral tests."""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from datetime import time as Time

from app.schemas.today import TodayMeta
from app.schemas.normalization import AstroSignal
from app.schemas.access import ContentAccessState


def test_today_meta_current_runtime():
    """Current production-style meta must still work (int versions, no canon_versions)."""
    meta = TodayMeta(
        schema_version="today/v1",
        contract_version=2,
        calculation_version=1,
        normalization_version=1,
        scoring_version=1,
        prompt_version=2,
        content_version=9,
        generated_at="2026-07-08T12:00:00Z",
        cached=False,
        scoring_canon_version=1,
        activation_layer_version=None,
    )
    assert isinstance(meta.scoring_version, int)
    assert meta.scoring_version == 1
    assert meta.activation_layer_version is None
    assert meta.canon_versions is None


def test_today_meta_v2_string_versions():
    """V2 string versions must be accepted too."""
    meta = TodayMeta(
        schema_version="today/v1",
        contract_version=2,
        calculation_version=1,
        normalization_version=1,
        scoring_version="ss-scoring-1.0",
        prompt_version=2,
        content_version=9,
        generated_at="2026-07-08T12:00:00Z",
        cached=False,
        scoring_canon_version=None,
        activation_layer_version="al-1.0",
        canon_versions={"spheres": "v1", "aspect_rules": "v1"},
        audit_trace_id="trace-abc-123",
    )
    assert isinstance(meta.scoring_version, str)
    assert meta.scoring_version == "ss-scoring-1.0"
    assert meta.activation_layer_version == "al-1.0"
    assert meta.canon_versions == {"spheres": "v1", "aspect_rules": "v1"}
    assert meta.audit_trace_id == "trace-abc-123"


def test_today_meta_includes_all_canon_versions():
    """Runtime TodayMeta should carry all expected canon version keys."""
    from app.services.canon_service import get_canon_versions
    versions = get_canon_versions()
    for key in ("spheres", "dignities", "aspect_rules", "activation_rules", "scoring_v2"):
        assert key in versions
    assert versions["spheres"] == "v1"
    assert len(versions) >= 5


def test_activation_layer_version_is_al_1_0_in_live_payload():
    """Schema-level check: ActivationLayerMeta defaults to al-1.0."""
    from app.schemas.activation import ActivationLayer
    from app.services.activation_layer_service import ActivationLayerService
    from datetime import date
    service = ActivationLayerService()
    layer = service.build(
        natal_context={}, transits={}, day_signals=[],
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    assert layer.activation_layer_version == "al-1.0"


@pytest.mark.asyncio
async def test_today_service_fresh_payload_activation_layer_wiring(db_session):
    """Full fresh TodayPayload path must wire activation_layer correctly:
    - build_why_contexts receives an ActivationLayer with version al-1.0
    - the layer contains transit_to_natal and transit_planet_in_house activations
    - returned payload meta has activation_layer_version al-1.0
    - scoring_version remains 1
    - ScoringService.score_day is called *exactly once* with *only* the
      deterministic transit-only day_signals, no activation_layer in args"""
    from datetime import date as Date
    from sqlalchemy import select
    from app.db.models import User, UserProfile
    from app.services.today_service import TodayService
    from app.services.access_service import AccessService
    from app.schemas.natal import (
        NatalContextData, NatalChartPlanet, NatalChartHouse,
        NatalChartAngle, NatalChartSpecialPoint,
    )

    # Create a user + profile in the in-memory DB
    user = User(tg_user_id=777777, tg_username="test_w3")
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

    # ── Deterministic fixtures ──────────────────────────────────────

    # NatalContextData: returned by patched NatalContextService.
    # Must have at least house_system so ActivationLayerService.build
    # does not crash on natal_context_dict.get("house_system", …).
    fake_natal_context = NatalContextData(
        house_system="WHOLE_SIGN",
        planets=[
            NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11),
            NatalChartPlanet(name="Moon", sign="Gemini", degree=30.0, longitude=119.63, retrograde=False, house=4),
            NatalChartPlanet(name="Pluto", sign="Scorpio", degree=25.0, longitude=234.78, retrograde=False, house=9),
            NatalChartPlanet(name="Mars", sign="Cancer", degree=8.0, longitude=137.95, retrograde=True, house=5),
        ],
        houses=[NatalChartHouse(number=i, sign="Aries" if i == 1 else "Taurus", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)],
    )

    # Deterministic transit data for the mocked get_solarsage_client
    mock_transit_data = {
        "target_jd": 2461229.875,
        "planets": [
            {"name": "Moon", "longitude": 23.37, "sign": "Aries", "retrograde": False, "speed": 13.73},
            {"name": "Mars", "longitude": 66.07, "sign": "Gemini", "retrograde": False, "speed": 0.70},
        ],
    }

    # Deterministic normalized signals returned by patched normalize_day
    transit_aspect = AstroSignal(
        type="aspect",
        planet="Transit_Moon",
        target_planet="Pluto",
        aspect_type="opposition",
        orb=1.0,
        strength=0.9,
    )
    transit_house = AstroSignal(
        type="planet_in_house",
        planet="Transit_Mars",
        house=12,
        strength=1.0,
    )
    static_background = AstroSignal(
        type="planet_in_house",
        planet="Sun",
        house=5,
        strength=1.0,
    )
    deterministic_signals = [transit_aspect, transit_house, static_background]

    # ── Mocks ───────────────────────────────────────────────────────

    from app.services.scoring_service import ScoringService
    mock_scoring = MagicMock(wraps=ScoringService())
    mock_scoring.score_day = MagicMock(wraps=mock_scoring.score_day)

    from app.services.semantic_service import SemanticService
    real_build_why = SemanticService.build_why_contexts
    captured_kwargs = {}

    def mock_build_why(service_self, *args, **kwargs):
        captured_kwargs.update(kwargs)
        return real_build_why(service_self, *args, **kwargs)

    with \
         patch("app.services.today_service.get_solarsage_client") as mock_client_factory, \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_get_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_normalize, \
         patch.object(TodayService, "_get_yesterday_signals") as mock_get_ys, \
         patch.object(SemanticService, "build_why_contexts", mock_build_why), \
         patch("app.services.today_service.ScoringService", return_value=mock_scoring):

        # NatalContextService returns a deterministic NatalContextData
        mock_get_natal.return_value = fake_natal_context

        # normalize_day returns deterministic signals
        mock_normalize.return_value = deterministic_signals

        # No yesterday data — DayDeltaService is skipped
        mock_get_ys.return_value = None

        # SolarSage client returns deterministic transits (for activation layer)
        mock_client = AsyncMock()
        mock_client.get_transits = AsyncMock(return_value=mock_transit_data)
        mock_client_factory.return_value = mock_client

        access = await AccessService(db_session).can_access_day(user.id, Date(2026, 7, 8))
        service = TodayService(db_session)
        payload = await service.get_today_payload(
            user_id=user.id,
            target_date=Date(2026, 7, 8),
            access_state=access,
            skip_prefetch=True,
        )

    # ── 1. Activation layer wired into build_why_contexts ───────────
    assert "activation_layer" in captured_kwargs, \
        "build_why_contexts must receive activation_layer"
    act_layer = captured_kwargs["activation_layer"]
    assert act_layer is not None
    assert act_layer.activation_layer_version == "al-1.0"
    assert len(act_layer.activations) > 0

    t2n = [a for a in act_layer.activations if a.technique == "transit_to_natal"]
    assert len(t2n) >= 1, "Expected at least one transit_to_natal activation"

    tih = [a for a in act_layer.activations if a.technique == "transit_planet_in_house"]
    assert len(tih) >= 1, "Expected at least one transit_planet_in_house activation"

    # ── 2. Returned payload meta ────────────────────────────────────
    assert payload.meta.activation_layer_version == "al-1.0"
    assert payload.meta.scoring_version == 1

    # ── 3. Strict scoring assertions ────────────────────────────────
    # Exactly one call
    assert mock_scoring.score_day.call_count == 1, \
        f"Expected exactly 1 call to score_day, got {mock_scoring.score_day.call_count}"

    call_args, call_kwargs = mock_scoring.score_day.call_args
    # Only the signals list as a positional argument
    assert len(call_args) == 1, \
        f"Expected exactly 1 positional arg, got {len(call_args)}"
    assert call_kwargs == {}, \
        f"Expected no keyword args, got {call_kwargs}"

    # The signals list must contain only the transit signals
    # (static_background with planet='Sun' is filtered by filter_day_scored_signals)
    actual_signals = call_args[0]
    assert isinstance(actual_signals, list)
    assert len(actual_signals) == 2, \
        f"Expected 2 transit-only signals, got {len(actual_signals)}"

    # Verify each signal independently (id comparison is fragile)
    assert actual_signals[0].planet == "Transit_Moon"
    assert actual_signals[0].type == "aspect"
    assert actual_signals[0].target_planet == "Pluto"

    assert actual_signals[1].planet == "Transit_Mars"
    assert actual_signals[1].type == "planet_in_house"
    assert actual_signals[1].house == 12

    # No ActivationLayer appears in scoring args
    from app.schemas.activation import ActivationLayer
    assert all(not isinstance(arg, ActivationLayer) for arg in call_args), \
        "ActivationLayer must not appear in scoring call args"


@pytest.mark.asyncio
async def test_today_service_locked_preview_no_activation_layer(db_session):
    """Locked preview payload must not claim an activation layer."""
    from datetime import date as Date
    from sqlalchemy import select
    from app.db.models import User, UserProfile
    from app.services.today_service import TodayService
    from unittest.mock import patch, AsyncMock

    user = User(tg_user_id=888888, tg_username="test_w2_locked")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id,
        first_name="Test",
        birthday=Date(1990, 1, 15),
        birth_time=None,
        birth_city="Moscow",
        birth_tz="Europe/Moscow",
        is_onboarded=True,
    )
    db_session.add(profile)
    await db_session.commit()

    locked_access = ContentAccessState(
        state="locked",
        reason="outside_access_window",
    )

    with patch("app.services.today_service.get_solarsage_client") as mock_client_factory:
        mock_client = AsyncMock()
        mock_client.get_transits = AsyncMock(return_value={"target_jd": 0, "planets": []})
        mock_client_factory.return_value = mock_client

        service = TodayService(db_session)
        payload = await service.get_today_payload(
            user_id=user.id,
            target_date=Date(2026, 7, 8),
            access_state=locked_access,
            skip_prefetch=True,
        )

    assert payload.access.state == "locked"
    assert payload.meta.activation_layer_version is None, "Locked preview must not have activation layer"
    assert payload.meta.scoring_version == 1


def test_today_service_not_wired_to_sidecar_activation_layer():
    """W3.4 guard: TodayService must not pass sidecar_activation_layer to
    ActivationLayerService.build(). Only None is allowed in W3.4.

    This test protects the W3 boundary: future waves must explicitly decide
    when to wire the sidecar layer.
    """
    from pathlib import Path
    source_path = Path(__file__).resolve().parent.parent / "app" / "services" / "today_service.py"
    source = source_path.read_text()
    import re
    # Look for non-None sidecar_activation_layer assignments
    matches = re.findall(
        r'sidecar_activation_layer=(?!None)',
        source,
    )
    assert not matches, (
        f"TodayService wires sidecar_activation_layer to a non-None value. "
        f"This is forbidden in W3.4. Found {len(matches)} non-None references."
    )
    # Also verify the None line exists
    assert "sidecar_activation_layer=None" in source, (
        "TodayService must contain 'sidecar_activation_layer=None' "
        "in its get_today_payload method."
    )
