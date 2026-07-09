"""Tests: W5 Calendar V2 dual-run integration."""
import pytest
from unittest.mock import AsyncMock, patch
from datetime import date as Date, time as Time
from app.db.models import User, UserProfile
from app.services.calendar_service import CalendarService
from app.core.config import settings
from app.services.day_scoring_runtime_service import DayScoringRuntimeService


def test_calendar_v2_dual_run_default(monkeypatch):
    """Default dual-run calendar status uses V1 via runtime service."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    from app.schemas.normalization import AstroSignal
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == 1
    assert result.v2_result is not None


def test_calendar_v2_enabled_status(monkeypatch):
    """V2-enabled calendar uses V2 status through runtime service."""
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    from app.schemas.normalization import AstroSignal
    signals = [AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=1.0, kind="aspect")]
    runtime = DayScoringRuntimeService()
    result = runtime.compute(signals)
    assert result.selected_scoring_version == "ss-scoring-2.0"


@pytest.mark.asyncio
async def test_calendar_service_dual_run_fetches_sidecar_activation(db_session, monkeypatch):
    """CalendarService in dual-run mode fetches sidecar activation-layer
    containing non-W2 technique (annual_profection) and passes it to V2."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    user = User(tg_user_id=888881, tg_username="test_cal_dual")
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

    original_compute = DayScoringRuntimeService.compute
    captured_layers = []

    def spy_compute(self_service, day_signals, activation_layer=None, **kwargs):
        captured_layers.append(activation_layer)
        return original_compute(self_service, day_signals, activation_layer=activation_layer, **kwargs)

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(DayScoringRuntimeService, "compute", spy_compute):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        status = await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        mock_client.get_activation_layer.assert_awaited()
        assert len(captured_layers) == 1
        al = captured_layers[0]
        assert al is not None
        profs = [a for a in al.activations if a.technique == "annual_profection"]
        assert len(profs) == 1
        assert profs[0].id == "annual_profection__LORD_OF_YEAR__MARS"
        assert status in ("supportive", "steady", "tense")


@pytest.mark.asyncio
async def test_calendar_service_v1_only_no_sidecar_call(db_session, monkeypatch):
    """CalendarService in V1-only mode does not call get_activation_layer()."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    user = User(tg_user_id=888882, tg_username="test_cal_v1")
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

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm:

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        mock_client.get_activation_layer.assert_not_awaited()


@pytest.mark.asyncio
async def test_calendar_service_shadow_fail_open_logs_fallback(db_session, monkeypatch):
    """CalendarService in dual-run shadow mode: sidecar failure returns status and logs fallback."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
    monkeypatch.setattr(settings, "solarsage_v2_enabled", False)

    user = User(tg_user_id=888883, tg_username="test_cal_shadow")
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

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm, \
         patch("app.core.logging.log_event", side_effect=capture_log_event):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        status = await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        assert status in ("supportive", "steady", "tense")
        assert "scoring.v2_diff" in log_events


@pytest.mark.asyncio
async def test_calendar_service_v2_enabled_fail_loud(db_session, monkeypatch):
    """CalendarService in V2-enabled mode: sidecar failure raises and does not log fallback."""
    monkeypatch.setattr(settings, "solarsage_v2_enabled", True)

    user = User(tg_user_id=888884, tg_username="test_cal_fail")
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

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm, \
         patch("app.core.logging.log_event", side_effect=capture_log_event):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        with pytest.raises(Exception):
            await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        fallback_logged = any("fallback" in str(e) for e in log_events)
        assert not fallback_logged


@pytest.mark.asyncio
async def test_calendar_service_current_location_complete_passed(db_session, monkeypatch):
    """Complete current location is passed to get_activation_layer in CalendarService."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)

    user = User(tg_user_id=888885, tg_username="test_cal_loc")
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

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm:

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        call_kwargs = mock_client.get_activation_layer.call_args.kwargs
        assert call_kwargs.get("current_location") == {"lat": 43.5, "lon": 39.5, "tz": "Europe/Moscow"}


@pytest.mark.asyncio
async def test_calendar_service_current_location_incomplete_omitted(db_session, monkeypatch):
    """Incomplete current location (missing current_tz) omits current_location in CalendarService."""
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)

    user = User(tg_user_id=888886, tg_username="test_cal_loc_inc")
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

    with patch("app.services.calendar_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.calendar_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.calendar_service.NormalizationService.normalize_day") as mock_norm:

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        service = CalendarService(db_session)
        await service._prepare_request_context(user.id)
        await service._compute_and_cache_day_status(user.id, Date(2026, 7, 8))

        call_kwargs = mock_client.get_activation_layer.call_args.kwargs
        assert call_kwargs.get("current_location") is None
