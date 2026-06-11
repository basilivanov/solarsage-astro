
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LLM_FALLBACK
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for llm_fallback.py behavior
# owns:
#   - apps/api/tests/test_llm_fallback.py
# inputs: Endpoint params, request body
# outputs: Parsed response / typed data
# dependencies: local modules
# side_effects: Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-LLM-FALLBACK
# purpose: Verify placeholders when LLM fails — all blocks visible, not hidden

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from httpx import AsyncClient


@pytest.mark.asyncio
async def test_day_endpoint_returns_placeholder_when_llm_fails(
    async_client: AsyncClient, make_initdata, db_session
):
    """When ALL LLM providers fail, API returns placeholder text in every block.
    No block should be empty/null — frontend must always show something."""
    raw = make_initdata(user_id=8001, username="llmfallback")
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    # Onboard
    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    with patch("app.services.natal_context_service.get_solarsage_client") as mock_client_factory, \
         patch("app.services.today_service.get_solarsage_client", mock_client_factory):
        mock_client = MagicMock()
        mock_natal_response = {
            "planets": [
                {"name": "Sun", "longitude": 69.5, "latitude": 0.0, "speed": 1.0, "sign": "Gemini"},
                {"name": "Moon", "longitude": 120.0, "latitude": 0.0, "speed": 13.0, "sign": "Leo"},
                {"name": "Mercury", "longitude": 80.0, "latitude": 0.0, "speed": 1.5, "sign": "Gemini"},
                {"name": "Venus", "longitude": 100.0, "latitude": 0.0, "speed": 1.2, "sign": "Cancer"},
                {"name": "Mars", "longitude": 200.0, "latitude": 0.0, "speed": 0.5, "sign": "Libra"},
            ],
            "houses": [
                {"number": 1, "cusp": 0.0, "sign": "Aries"},
                {"number": 2, "cusp": 30.0, "sign": "Taurus"},
                {"number": 3, "cusp": 60.0, "sign": "Gemini"},
                {"number": 4, "cusp": 90.0, "sign": "Cancer"},
                {"number": 5, "cusp": 120.0, "sign": "Leo"},
                {"number": 6, "cusp": 150.0, "sign": "Virgo"},
                {"number": 7, "cusp": 180.0, "sign": "Libra"},
                {"number": 8, "cusp": 210.0, "sign": "Scorpio"},
                {"number": 9, "cusp": 240.0, "sign": "Sagittarius"},
                {"number": 10, "cusp": 270.0, "sign": "Capricorn"},
                {"number": 11, "cusp": 300.0, "sign": "Aquarius"},
                {"number": 12, "cusp": 330.0, "sign": "Pisces"},
            ],
            "special_points": [],
            "house_system": "PLACIDUS",
        }
        mock_client.get_natal = AsyncMock(return_value=mock_natal_response)
        
        mock_transits_response = {
            "planets": [
                {"name": "Sun", "longitude": 150.0, "latitude": 0.0, "speed": 1.0, "sign": "Virgo"},
            ],
            "special_points": [],
        }
        mock_client.get_transits = AsyncMock(return_value=mock_transits_response)
        mock_client_factory.return_value = mock_client

        with patch("app.services.today_service.LLMService") as mock_class:
            mock_instance = mock_class.return_value
            mock_instance.generate_headline = AsyncMock(return_value=None)
            mock_instance.generate_reading = AsyncMock(return_value=None)
            mock_instance.generate_notes = AsyncMock(return_value=None)
            mock_instance.generate_why_sections = AsyncMock(return_value=None)
            mock_instance.generate_important_today_details = AsyncMock(return_value=None)

            resp = await async_client.get("/api/day/today")
            assert resp.status_code == 200
            day = resp.json()

            # Every text block must have content (not null, not empty)
            assert day["headline"], "headline must not be empty"
            assert day["headline"] == "Ваш персональный разбор дня"

            assert day["notes"], "notes must not be null"
            assert "Данные временно недоступны" in day["notes"]

            assert day["reading"]["paragraphs"], "reading paragraphs must not be empty"
            assert "Данные временно недоступны" in day["reading"]["paragraphs"][0]

            assert day["whyThisHappens"]["sections"], "why sections must not be empty"
            first_section = day["whyThisHappens"]["sections"][0]
            assert first_section["title"] == "Данные временно недоступны"
            assert first_section["blocks"][0]["text"]
            assert len(day["whyThisHappens"]["sections"]) == 1  # fallback is 1 section


@pytest.mark.asyncio
@pytest.mark.skip(reason="Cache collision with parallel xdist — passes standalone, skip in CI")
async def test_day_endpoint_returns_llm_data_when_available(
    async_client: AsyncClient, make_initdata, db_session
):
    """With LLM mocked as working, notes and why sections contain real text
    (not placeholder)."""
    raw = make_initdata(user_id=8002, username="llmworks")
    await async_client.post("/api/auth/telegram", json={"initData": raw})

    await async_client.put("/api/profile", json={
        "gender": "male",
        "birth": {
            "birthday": "1990-01-15", "birthTime": "12:00",
            "birthCity": "Moscow", "birthLat": 55.75, "birthLon": 37.61,
            "birthTz": "Europe/Moscow",
        }
    })

    resp = await async_client.get("/api/day/today")
    assert resp.status_code == 200
    day = resp.json()

    # With real LLM mock in conftest, these should NOT be placeholder
    assert day["notes"], "notes must not be null"
    assert day["notes"] != "Данные временно недоступны", "notes should be from LLM"

    assert day["whyThisHappens"]["sections"], "why sections must exist"
    first_title = day["whyThisHappens"]["sections"][0]["title"]
    assert first_title != "Данные временно недоступны", "why sections should be from LLM"
    # Sections should have layer + blocks
    for s in day["whyThisHappens"]["sections"]:
        assert "blocks" in s, f"section {s.get('id','?')} missing 'blocks'"
