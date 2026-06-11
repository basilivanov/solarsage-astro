
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_TRANSITS
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/tests/test_transits.py
# owns:
#   - apps/solarsage/tests/test_transits.py
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
# module: M-SIDECAR-TEST-TRANSITS
# wave: W-3.3
# purpose: Transits endpoint tests

import pytest
from httpx import AsyncClient, ASGITransport

from solarsage.app import app


@pytest.mark.asyncio
async def test_transits_endpoint():
    """POST /v1/transits returns transit planets."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/transits", json={
            "target_date": "2026-05-30",
            "target_time": "12:00",
            "target_tz": "Europe/Moscow",
        })

        assert response.status_code == 200
        data = response.json()

        # Check structure
        assert "planets" in data
        assert "target_jd" in data

        # Check planets (10 planets)
        assert len(data["planets"]) == 10

        # Check Sun position
        sun = next(p for p in data["planets"] if p["name"] == "Sun")
        assert 0 <= sun["longitude"] <= 360
        assert sun["sign"] in ["Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
                                "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"]

        # Check that target_jd is reasonable (around 2026)
        # JD for 2026-05-30 should be around 2461190
        assert 2461000 < data["target_jd"] < 2462000


@pytest.mark.asyncio
async def test_transits_different_timezone():
    """Transits work with different timezones."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # UTC
        response_utc = await client.post("/v1/transits", json={
            "target_date": "2026-05-30",
            "target_time": "12:00",
            "target_tz": "UTC",
        })

        # Moscow (UTC+3)
        response_moscow = await client.post("/v1/transits", json={
            "target_date": "2026-05-30",
            "target_time": "15:00",  # Same moment as 12:00 UTC
            "target_tz": "Europe/Moscow",
        })

        assert response_utc.status_code == 200
        assert response_moscow.status_code == 200

        # Same moment should have same JD (within small tolerance)
        jd_utc = response_utc.json()["target_jd"]
        jd_moscow = response_moscow.json()["target_jd"]

        assert abs(jd_utc - jd_moscow) < 0.001  # ~1 minute tolerance
