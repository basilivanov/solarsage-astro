import json
from pathlib import Path
from datetime import date as Date, time as Time
from unittest.mock import AsyncMock, patch
import pytest
from app.db.models import User, UserProfile
from app.schemas.access import ContentAccessState
from app.services.today_service import TodayService
from app.core.config import settings

@pytest.mark.asyncio
async def test_basil_golden_v1_v2_comparison(db_session, monkeypatch):
    """Verify live pipeline outputs for Basil 2026-07-08 match golden files within W7 tolerances."""
    # Create a completely scrubbed mock user and profile
    user = User(tg_user_id=12345, tg_username="mock_user")
    db_session.add(user)
    await db_session.flush()
    profile = UserProfile(
        user_id=user.id,
        first_name="Mock",
        birthday=Date(1990, 1, 15),
        birth_time=Time(12, 0),
        birth_city="MockCity",
        birth_lat=55.76,
        birth_lon=37.62,
        gender="male",
        birth_tz="Europe/Moscow",
        is_onboarded=True,
        current_lat=55.76,
        current_lon=37.62,
        current_tz="Europe/Moscow",
    )
    db_session.add(profile)
    await db_session.commit()

    # Load golden fixtures using repo-relative paths
    golden_dir = Path(__file__).resolve().parent / "fixtures" / "golden"
    golden_v1 = json.loads((golden_dir / "basil_2026_07_08_v1.json").read_text(encoding="utf-8"))
    golden_v2 = json.loads((golden_dir / "basil_2026_07_08_v2.json").read_text(encoding="utf-8"))

    # Load scrubbed inputs from the golden inputs directory
    raw_transits = json.loads((golden_dir / "inputs" / "raw_transits.json").read_text(encoding="utf-8"))
    raw_activations = json.loads((golden_dir / "inputs" / "raw_activations.json").read_text(encoding="utf-8"))
    raw_natal = json.loads((golden_dir / "inputs" / "raw_natal_context.json").read_text(encoding="utf-8"))

    from app.schemas.natal import NatalContextData
    mock_natal_data = NatalContextData.model_validate(raw_natal)

    mock_client = AsyncMock()
    mock_client.get_transits = AsyncMock(return_value=raw_transits)
    mock_client.get_activation_layer = AsyncMock(return_value=raw_activations)

    with patch("app.services.today_service.get_solarsage_client", return_value=mock_client), \
         patch("app.services.today_service.NatalContextService.get_or_build_natal_context", return_value=mock_natal_data), \
         patch("app.services.llm_service.LLMService.generate_headline", return_value="День для важных решений и переговоров"), \
         patch("app.services.llm_service.LLMService.generate_reading", return_value=["Сегодня день возможностей. Марс в гармоничном аспекте с Юпитером даёт прилив уверенности."]), \
         patch("app.services.llm_service.LLMService.generate_notes", return_value="Хороший день для творчества и общения с близкими."), \
         patch("app.services.llm_service.LLMService.generate_why_sections", return_value=[
             {"id": "why-1", "title": "Лунное влияние", "blocks": [{"kind": "paragraph", "text": "Луна в Раке усиливает интуицию."}]}
         ]):

        access = ContentAccessState(state="full")
        service = TodayService(db_session)

        # 1. Compare V1
        monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", False)
        monkeypatch.setattr(settings, "solarsage_v2_enabled", False)
        monkeypatch.setattr(settings, "solarsage_v2_dual_run", False)

        payload_v1 = await service.get_today_payload(
            user_id=user.id,
            target_date=Date(2026, 7, 8),
            access_state=access,
            skip_prefetch=True,
        )
        live_v1 = json.loads(payload_v1.model_dump_json(by_alias=True))

        assert live_v1["dayStatus"] == golden_v1["dayStatus"]
        assert len(live_v1["topFlags"]) == len(golden_v1["topFlags"])
        for i in range(len(live_v1["topFlags"])):
            assert live_v1["topFlags"][i]["title"] == golden_v1["topFlags"][i]["title"]

        # Compare sphere scores (v1)
        for s1, s2 in zip(sorted(live_v1["sphereScores"], key=lambda x: x["key"]),
                          sorted(golden_v1["sphereScores"], key=lambda x: x["key"])):
            assert abs(s1["score"] - s2["score"]) <= 0.02

        # 2. Compare V2
        monkeypatch.setattr(settings, "solarsage_v2_frontend_enabled", True)
        monkeypatch.setattr(settings, "solarsage_v2_enabled", True)
        monkeypatch.setattr(settings, "solarsage_v2_dual_run", True)
        await service.invalidate_cache(user.id)

        payload_v2 = await service.get_today_payload(
            user_id=user.id,
            target_date=Date(2026, 7, 8),
            access_state=access,
            skip_prefetch=True,
        )
        live_v2 = json.loads(payload_v2.model_dump_json(by_alias=True))

        assert live_v2["dayStatus"] == golden_v2["dayStatus"]
        assert live_v2["v2"] is not None

        # Compare V2 sphere scores breakdown
        for k, score_v2 in live_v2["v2"]["scoreBreakdown"].items():
            golden_score = golden_v2["v2"]["scoreBreakdown"].get(k)
            assert golden_score is not None
            assert abs(score_v2["finalScore"] - golden_score["finalScore"]) <= 0.02
