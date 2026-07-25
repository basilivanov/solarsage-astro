# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SYNASTRY
# ROLE: Sidecar synastry endpoint tests
# DEPENDENCIES: pytest, httpx, solarsage.app
# GRACE_ANCHORS: []
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-TEST-SYNASTRY
# purpose: Test POST /v1/synastry calculation endpoint and precision invariants.
# owns:
#   - apps/solarsage/tests/test_synastry.py
# inputs: Synastry calculation JSON requests
# outputs: Assertions on positions, aspects, and precision flags
# dependencies: pytest, httpx, solarsage.app
# side_effects: none
# emitted_logs: none
# failure_policy: pytest test failure
# END_MODULE_CONTRACT: M-SIDECAR-TEST-SYNASTRY

# START_MODULE_MAP: M-SIDECAR-TEST-SYNASTRY
# public_entrypoints:
#   - test_synastry_endpoint_exact
#   - test_synastry_endpoint_approximate
# semantic_blocks: none
# owned_tests: none
# END_MODULE_MAP: M-SIDECAR-TEST-SYNASTRY

import pytest
from httpx import ASGITransport, AsyncClient

from solarsage.app import app

pytestmark = pytest.mark.usefixtures("moshier_mode")


@pytest.mark.asyncio
async def test_synastry_endpoint_exact():
    """POST /v1/synastry with exact time returns planets, houses, and cross-aspects."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/synastry",
            json={
                "owner_birth_date": "1990-01-15",
                "owner_birth_time": "12:00",
                "owner_birth_lat": 55.7558,
                "owner_birth_lon": 37.6173,
                "owner_birth_tz": "Europe/Moscow",
                "partner_birth_date": "1992-05-20",
                "partner_birth_time": "15:30",
                "partner_birth_lat": 59.9343,
                "partner_birth_lon": 30.3351,
                "partner_birth_tz": "Europe/Moscow",
                "partner_birth_time_precision": "exact",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert "owner_planets" in data
        assert "partner_planets" in data
        assert data["partner_houses"] is not None
        assert "cross_aspects" in data
        assert data["precision_flags"]["houses_available"] is True
        assert data["precision_flags"]["report_precision"] == "exact"


@pytest.mark.asyncio
async def test_synastry_endpoint_approximate():
    """POST /v1/synastry with approximate time sets houses=None and precision=approximate."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/synastry",
            json={
                "owner_birth_date": "1990-01-15",
                "owner_birth_time": "12:00",
                "owner_birth_lat": 55.7558,
                "owner_birth_lon": 37.6173,
                "owner_birth_tz": "Europe/Moscow",
                "partner_birth_date": "1992-05-20",
                "partner_birth_time": None,
                "partner_birth_lat": None,
                "partner_birth_lon": None,
                "partner_birth_tz": None,
                "partner_birth_time_precision": "approximate",
            },
        )

        assert response.status_code == 200
        data = response.json()
        assert data["partner_houses"] is None
        assert data["partner_special_points"] is None
        assert data["precision_flags"]["houses_available"] is False
        assert data["precision_flags"]["report_precision"] == "approximate"
