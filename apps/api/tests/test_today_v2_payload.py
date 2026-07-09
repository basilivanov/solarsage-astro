import pytest
from datetime import date as Date, time as Time
from unittest.mock import AsyncMock, patch, MagicMock
from app.db.models import User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService
from app.core.config import settings

@pytest.mark.asyncio
async def test_today_payload_v2_block_included_when_flag_enabled(db_session, monkeypatch):
    """If settings.solarsage_v2_frontend_enabled is True, TodayPayload must have v2 block,
    payload_version='today.v2', and frontend_payload_version=2."""
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)
    monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)

    user = User(tg_user_id=888891, tg_username="test_v2_payload")
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
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "1", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "WHOLE_SIGN",
        "activations": [],
        "by_planet": {}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    })
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"), \
        patch("app.services.llm_service.LLMService.generate_headline", return_value="Test Headline"), \
        patch("app.services.llm_service.LLMService.generate_reading", return_value=["Reading text"]), \
        patch("app.services.llm_service.LLMService.generate_notes", return_value="Notes text"), \
        patch("app.services.llm_service.LLMService.generate_why_sections", return_value=[]) as mock_why:

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="full")
        service = TodayService(db_session)
        payload = await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        assert payload.v2 is not None
        assert payload.meta.payload_version == "today.v2"
        assert payload.meta.frontend_payload_version == 2

        mock_why.assert_called_once()
        why_call_kwargs = mock_why.call_args.kwargs
        assert "evidence_packet" in why_call_kwargs
        assert why_call_kwargs["evidence_packet"] is not None
        assert why_call_kwargs["evidence_packet"]["day_status"] == "steady"

@pytest.mark.asyncio
async def test_today_payload_v2_block_omitted_when_flag_disabled(db_session, monkeypatch):
    """If settings.solarsage_v2_frontend_enabled is False, TodayPayload must have v2=None,
    payload_version='today.v1', and frontend_payload_version=1."""
    monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", False)

    user = User(tg_user_id=888892, tg_username="test_v2_disabled")
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
    mock_client.get_activation_layer = AsyncMock(return_value={
        "schema_version": "activation-layer.v1", "activation_layer_version": "al-1.0",
        "calculation_version": "1", "target_date": "2026-07-08", "target_time": "12:00",
        "target_tz": "Europe/Moscow", "house_system": "WHOLE_SIGN",
        "activations": [],
        "by_planet": {}, "by_house": {}, "by_lot": {}, "by_angle": {}, "warnings": [],
    })
    mock_client.get_transits = AsyncMock(return_value={"target_jd": 2461229.875, "planets": []})

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context") as mock_natal, \
         patch("app.services.today_service.NormalizationService.normalize_day") as mock_norm, \
         patch.object(TodayService, "_get_yesterday_signals", return_value=None), \
         patch.object(TodayService, "_cache_payload"), \
         patch.object(TodayService, "_cache_semantic_layer"), \
         patch("app.services.llm_service.LLMService.generate_headline", return_value="Test Headline"), \
         patch("app.services.llm_service.LLMService.generate_reading", return_value=["Reading text"]), \
         patch("app.services.llm_service.LLMService.generate_notes", return_value="Notes text"), \
         patch("app.services.llm_service.LLMService.generate_why_sections", return_value=[]):

        from app.schemas.natal import NatalContextData, NatalChartPlanet, NatalChartHouse
        fake_natal = NatalContextData(house_system="WHOLE_SIGN", planets=[NatalChartPlanet(name="Sun", sign="Capricorn", degree=7.0, longitude=286.93, retrograde=False, house=11)], houses=[NatalChartHouse(number=i, sign="Aries", degree=0.0, longitude=float((i - 1) * 30)) for i in range(1, 13)])
        mock_natal.return_value = fake_natal
        mock_norm.return_value = []

        access = ContentAccessState(state="full")
        service = TodayService(db_session)
        payload = await service.get_today_payload(
            user_id=user.id, target_date=Date(2026, 7, 8),
            access_state=access, skip_prefetch=True,
        )

        assert payload.v2 is None
        assert payload.meta.payload_version == "today.v1"
        assert payload.meta.frontend_payload_version == 1
