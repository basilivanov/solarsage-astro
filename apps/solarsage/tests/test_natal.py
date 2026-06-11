
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_NATAL
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for natal.py behavior
# owns:
#   - apps/solarsage/tests/test_natal.py
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
# module: M-SIDECAR-TEST-NATAL
# wave: W-3.2
# purpose: Natal endpoint tests

import pytest
from httpx import AsyncClient, ASGITransport

from solarsage.app import app


@pytest.mark.asyncio
async def test_natal_endpoint():
    """POST /v1/natal returns planets, houses, special points."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/natal", json={
            "birth_date": "1990-01-15",
            "birth_time": "14:30",
            "birth_lat": 55.7558,
            "birth_lon": 37.6173,
            "birth_tz": "Europe/Moscow",
        })

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "planets" in data
        assert "houses" in data
        assert "special_points" in data
        assert "house_system" in data

        # Check planets (10 planets)
        assert len(data["planets"]) == 10
        sun = next(p for p in data["planets"] if p["name"] == "Sun")
        assert 0 <= sun["longitude"] <= 360
        assert sun["sign"] in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # Check houses (12 houses)
        assert len(data["houses"]) == 12

        # Check special points (ASC, MC, etc)
        assert len(data["special_points"]) >= 4
        asc = next(sp for sp in data["special_points"] if sp["name"] == "ASC")
        assert 0 <= asc["longitude"] <= 360


@pytest.mark.asyncio
async def test_natal_high_latitude():
    """High latitude (>= 60 deg) uses WHOLE_SIGN house system."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/natal", json={
            "birth_date": "1980-10-30",
            "birth_time": "19:50",
            "birth_lat": 67.9387,  # Murmansk (high latitude)
            "birth_lon": 32.9241,
            "birth_tz": "Europe/Moscow",
        })

        assert response.status_code == 200
        data = response.json()

        # High latitude should use WHOLE_SIGN
        assert data["house_system"] == "WHOLE_SIGN"
