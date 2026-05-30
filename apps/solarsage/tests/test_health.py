# AI_HEADER
# module: M-SIDECAR-TEST-HEALTH
# wave: W-3.1
# purpose: Health endpoint tests

import pytest
from httpx import AsyncClient, ASGITransport

from solarsage.app import app


@pytest.mark.asyncio
async def test_health_endpoint():
    """GET /v1/health returns 200 with expected fields."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/v1/health")

        assert response.status_code == 200
        data = response.json()

        assert data["ok"] is True
        assert "version" in data
        assert "ephemeris_path" in data
        assert "calculation_version" in data
        assert data["calculation_version"] == "ss-1.0.0"


@pytest.mark.asyncio
async def test_root_endpoint():
    """GET / returns welcome message."""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get("/")

        assert response.status_code == 200
        data = response.json()

        assert "message" in data
        assert "docs" in data
