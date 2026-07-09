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

    from app.services.day_scoring_runtime_service import DayScoringRuntimeService, DualRunResult
    mock_runtime = MagicMock(wraps=DayScoringRuntimeService())
    mock_dual = MagicMock()
    mock_dual.selected_result = {
        "day_status": "supportive",
        "sphere_scores": {"thinking_speech_learning": 1.2},
        "top_signals": [],
    }
    mock_dual.selected_scoring_version = 1
    mock_dual.v1_result = {"day_status": "supportive", "sphere_scores": {}, "top_signals": []}
    mock_dual.v2_result = None
    mock_runtime.compute = MagicMock(return_value=mock_dual)

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
         patch("app.services.today_service.DayScoringRuntimeService", return_value=mock_runtime):

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

    # ── 3. Runtime service called correctly ──────────────────────────
    mock_runtime.compute.assert_called_once()
    # Verify activation layer was passed to runtime
    call_kwargs = mock_runtime.compute.call_args.kwargs
    assert "activation_layer" in call_kwargs
    assert call_kwargs["activation_layer"] is not None


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


@pytest.mark.asyncio
async def test_today_service_dual_run_fetches_sidecar_activation(db_session, monkeypatch):
    """TodayService in dual-run mode fetches sidecar activation-layer
    containing non-W2 technique (annual_profection) and passes it to V2."""
    from unittest.mock import AsyncMock, MagicMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings
    from app.services.day_scoring_runtime_service import DayScoringRuntimeService

    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    # Create user + profile
    user = User(tg_user_id=777777, tg_username="test_w5_dual")
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

    sidecar_layer_dict = {
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "1", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "WHOLE_SIGN",
        "activations": [{"id": "annual_profection__LORD_OF_YEAR__MARS", "technique": "annual_profection", "technique_family": "profection", "target_type": "planet", "target_key": "MARS", "kind": "lord_of_year", "active": True, "phase": "period", "polarity": "neutral", "strength": 0.75, "evidence": "Test annual profection"}],
        "by_planet": {"MARS": ["annual_profection__LORD_OF_YEAR__MARS"]},
        "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    }
    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock(return_value=sidecar_layer_dict)
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    # Spy on DayScoringRuntimeService.compute
    original_compute = DayScoringRuntimeService.compute
    captured_layers = []

    def spy_compute(self_service, day_signals, activation_layer=None, **kwargs):
        captured_layers.append(activation_layer)
        return original_compute(self_service, day_signals, activation_layer=activation_layer, **kwargs)

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"), \
         patch.object(DayScoringRuntimeService, "compute", spy_compute):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        # 1. Prove sidecar activation-layer was fetched
        mock_client.get_activation_layer.assert_awaited()
        # 2. Prove DayScoringRuntimeService.compute received an activation layer containing the profection
        assert len(captured_layers) == 1
        al = captured_layers[0]
        assert al is not None
        profs = [a for a in al.activations if a.technique == "annual_profection"]
        assert len(profs) == 1, "Expected annual_profection in the passed activation layer"
        assert profs[0].id == "annual_profection__LORD_OF_YEAR__MARS"


@pytest.mark.asyncio
async def test_today_service_v1_only_no_sidecar_call(db_session, monkeypatch):
    """V1-only mode must not call get_activation_layer()."""
    from unittest.mock import AsyncMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings

    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    user = User(tg_user_id=777778, tg_username="test_w5_v1")
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

    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        # Prove sidecar activation-layer was NOT fetched in V1-only mode
        mock_client.get_activation_layer.assert_not_awaited()


@pytest.mark.asyncio
async def test_today_service_shadow_fail_open_logs_fallback(db_session, monkeypatch):
    """Dual-run shadow mode: sidecar failure returns V1 and logs fallback."""
    from unittest.mock import AsyncMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings

    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    user = User(tg_user_id=777779, tg_username="test_w5_shadow")
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

    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock(side_effect=RuntimeError("sidecar down"))
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    log_events = []
    def capture_log_event(event, **kwargs):
        log_events.append(event)

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"), \
         patch("app.services.today_service.log_event", side_effect=capture_log_event):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        payload = await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        # Should return V1 payload (not crash)
        assert payload is not None
        assert payload.meta.scoring_version == 1
        # Should have logged the fallback marker
        assert "scoring.v2_diff" in log_events


@pytest.mark.asyncio
async def test_today_service_v2_enabled_fail_loud(db_session, monkeypatch):
    """V2-enabled mode: sidecar failure raises, no fallback log."""
    from unittest.mock import AsyncMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings

    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)

    user = User(tg_user_id=777780, tg_username="test_w5_fail")
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

    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock(side_effect=RuntimeError("sidecar down"))
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    log_events = []
    def capture_log_event(event, **kwargs):
        log_events.append(event)

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch("app.services.today_service.log_event", side_effect=capture_log_event):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        with pytest.raises(Exception):
            await service.get_today_payload(
                user_id=user.id, target_date=Date(2026, 7, 8),
                access_state=access, skip_prefetch=True,
            )
        # Must NOT log "using local fallback" in V2-enabled mode
        fallback_logged = any("fallback" in str(e) for e in log_events)
        assert not fallback_logged, "V2-enabled mode must not log fallback"


@pytest.mark.asyncio
async def test_today_service_current_location_complete_passed(db_session, monkeypatch):
    """Complete current location (lat, lon, tz) is passed to get_activation_layer."""
    from unittest.mock import AsyncMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings

    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)

    user = User(tg_user_id=777781, tg_username="test_w5_loc")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id, first_name="Test",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.76, birth_lon=37.62,
        gender="female", birth_tz="Europe/Moscow", is_onboarded=True,
        current_lat=43.5, current_lon=39.5, current_tz="Europe/Moscow",
    )
    db_session.add(profile)
    await db_session.commit()

    sidecar_layer_dict = {
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "1", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "WHOLE_SIGN",
        "activations": [],
        "by_planet": {}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    }
    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock(return_value=sidecar_layer_dict)
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        # Verify current_location parameter was passed to get_activation_layer
        call_kwargs = mock_client.get_activation_layer.call_args.kwargs
        assert call_kwargs.get("current_location") == {"lat": 43.5, "lon": 39.5, "tz": "Europe/Moscow"}


@pytest.mark.asyncio
async def test_today_service_current_location_incomplete_omitted(db_session, monkeypatch):
    """Missing current_tz in profile omits current_location entirely."""
    from unittest.mock import AsyncMock, patch
    from datetime import date as Date, time as Time
    from app.db.models import User, UserProfile
    from app.schemas.access import ContentAccessState
    from app.services.today_service import TodayService
    from app.core.config import settings

    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)

    user = User(tg_user_id=777782, tg_username="test_w5_loc_inc")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id, first_name="Test",
        birthday=Date(1990, 1, 15), birth_time=Time(12, 0),
        birth_city="Moscow", birth_lat=55.76, birth_lon=37.62,
        gender="female", birth_tz="Europe/Moscow", is_onboarded=True,
        current_lat=43.5, current_lon=39.5, current_tz=None,  # incomplete
    )
    db_session.add(profile)
    await db_session.commit()

    sidecar_layer_dict = {
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "1", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "WHOLE_SIGN",
        "activations": [],
        "by_planet": {}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    }
    mock_client = AsyncMock()
    mock_client.get_activation_layer = AsyncMock(return_value=sidecar_layer_dict)
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="preview", reason="expired_access")
        service = TodayService(db_session)
        await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        # Verify current_location parameter was None (omitted)
        call_kwargs = mock_client.get_activation_layer.call_args.kwargs
        assert call_kwargs.get("current_location") is None

def test_version_constants_are_explicit():
    from app.core.versions import (
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
        SCORING_V2_VERSION,
        TODAY_V2_PAYLOAD_VERSION,
        V2_FRONTEND_PAYLOAD_VERSION,
    )
    assert CALCULATION_VERSION.startswith("ss-calc-")
    assert ACTIVATION_LAYER_VERSION.startswith("al-")
    assert SCORING_V2_VERSION.startswith("ss-scoring-")
    assert TODAY_V2_PAYLOAD_VERSION == "today.v2"
    assert V2_FRONTEND_PAYLOAD_VERSION == 2


def test_api_and_sidecar_calculation_version_literals_match():
    """Package separation requires duplicated literals; keep them equal."""
    from app.core.versions import ACTIVATION_LAYER_VERSION as API_AL
    from app.core.versions import CALCULATION_VERSION as API_CALC
    # Sidecar path may not be importable from API tests; compare literal file content.
    from pathlib import Path
    text = Path(__file__).resolve().parents[3].joinpath(
        "apps/solarsage/solarsage/core/versions.py"
    ).read_text(encoding="utf-8")
    assert f'CALCULATION_VERSION = "{API_CALC}"' in text
    assert f'ACTIVATION_LAYER_VERSION = "{API_AL}"' in text


def test_activation_layer_service_uses_canonical_calculation_version():
    from datetime import date
    from app.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
    from app.services.activation_layer_service import ActivationLayerService

    layer = ActivationLayerService().build(
        natal_context={},
        transits={},
        day_signals=[],
        target_date=date(2026, 7, 8),
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
    )
    assert layer.calculation_version == CALCULATION_VERSION
    assert layer.activation_layer_version == ACTIVATION_LAYER_VERSION


def test_expected_cache_identity_v2_flags(monkeypatch):
    from uuid import uuid4
    from app.core.config import settings
    from app.core.versions import (
        ACTIVATION_LAYER_VERSION,
        CALCULATION_VERSION,
        SCORING_V2_VERSION,
        V2_FRONTEND_PAYLOAD_VERSION,
    )
    from app.services.cache_key_service import expected_cache_identity

    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)
    key = expected_cache_identity(
        user_id=uuid4(),
        target_date="2026-07-08",
        profile_hash="abc",
    )
    assert key.calculation_version == CALCULATION_VERSION
    assert key.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert key.scoring_version == SCORING_V2_VERSION
    assert key.frontend_payload_version == V2_FRONTEND_PAYLOAD_VERSION
