
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SOLARSAGE_CLIENT
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for solarsage_client.py behavior
# owns:
#   - apps/api/tests/test_solarsage_client.py
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
# module: M-TEST-SOLARSAGE-CLIENT
# wave: W-3.4
# purpose: SolarSage client tests

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from app.clients.solarsage_client import SolarSageClient


@pytest.mark.asyncio
async def test_get_natal():
    """SolarSage client calls POST /v1/natal."""
    client = SolarSageClient()

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "planets": [
            {
                "name": "Sun",
                "longitude": 69.5,
                "latitude": 0.0,
                "speed": 1.0,
                "sign": "Gemini",
            }
        ],
        "houses": [
            {
                "number": 1,
                "cusp": 10.0,
                "sign": "Aries",
            }
        ],
        "special_points": [],
        "house_system": "PLACIDUS",
    }
    mock_response.raise_for_status = MagicMock()

    # Mock the async post method
    mock_post = AsyncMock(return_value=mock_response)

    with patch.object(client.client, "post", mock_post):
        result = await client.get_natal(
            birth_date="1990-01-15",
            birth_time="14:30",
            birth_lat=55.7558,
            birth_lon=37.6173,
            birth_tz="Europe/Moscow",
        )

        # Check that POST was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/v1/natal"

        # Check payload
        payload = call_args[1]["json"]
        assert payload["birth_date"] == "1990-01-15"
        assert payload["birth_time"] == "14:30"
        assert payload["birth_lat"] == 55.7558
        assert payload["birth_lon"] == 37.6173
        assert payload["birth_tz"] == "Europe/Moscow"

        # Check result
        assert "planets" in result
        assert len(result["planets"]) == 1
        assert result["planets"][0]["name"] == "Sun"
        assert result["planets"][0]["latitude"] == 0.0


@pytest.mark.asyncio
async def test_get_transits():
    """SolarSage client calls POST /v1/transits."""
    client = SolarSageClient()

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "planets": [
            {
                "name": "Sun",
                "longitude": 69.5,
                "latitude": 0.0,
                "speed": 1.0,
                "sign": "Gemini",
            }
        ],
        "target_jd": 2461190.0,
    }
    mock_response.raise_for_status = MagicMock()

    # Mock the async post method
    mock_post = AsyncMock(return_value=mock_response)

    with patch.object(client.client, "post", mock_post):
        result = await client.get_transits(
            target_date="2026-05-30",
            target_time="12:00",
            target_tz="Europe/Moscow",
        )

        # Check that POST was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/v1/transits"

        # Check payload
        payload = call_args[1]["json"]
        assert payload["target_date"] == "2026-05-30"
        assert payload["target_time"] == "12:00"
        assert payload["target_tz"] == "Europe/Moscow"

        # Check result
        assert "planets" in result
        assert "targetJd" in result
        assert result["targetJd"] == 2461190.0
        assert result["planets"][0]["latitude"] == 0.0


@pytest.mark.asyncio
async def test_validation_errors():
    """SolarSageClient fails if sidecar response is invalid or missing required fields."""
    from pydantic import ValidationError
    from app.schemas.natal import SolarSageNatalResponse, SolarSageTransitsResponse

    # 1. Missing houses
    with pytest.raises(ValidationError):
        SolarSageNatalResponse.model_validate({
            "planets": [{"name": "Sun", "longitude": 69.5, "sign": "Gemini", "speed": 1.0}],
            "houses": [],
            "special_points": [],
        })

    # 2. Missing planets in transits
    with pytest.raises(ValidationError):
        SolarSageTransitsResponse.model_validate({
            "planets": [],
            "target_jd": 2461190.0,
        })
