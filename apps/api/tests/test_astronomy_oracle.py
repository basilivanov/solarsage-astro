import pytest
from app.clients.solarsage_client import SolarSageClient

@pytest.mark.asyncio
async def test_retrograde_flags_2026_07_08():
    client = SolarSageClient()
    try:
        res = await client.get_transits(
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow"
        )
        planets = {p["name"]: p for p in res["planets"]}
        
        assert planets["Mercury"]["retrograde"] is True
        assert planets["Neptune"]["retrograde"] is True
        assert planets["Pluto"]["retrograde"] is True
    finally:
        await client.client.aclose()

@pytest.mark.asyncio
async def test_moon_phase_illumination_2026_07_08():
    client = SolarSageClient()
    try:
        res = await client.get_transits(
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow"
        )
        planets = {p["name"]: p for p in res["planets"]}
        sun_lon = planets["Sun"]["longitude"]
        moon_lon = planets["Moon"]["longitude"]
        
        from math import radians, cos
        angle = (moon_lon - sun_lon) % 360
        illumination = (1 - cos(radians(angle))) / 2 * 100
        
        assert abs(illumination - 43.792) <= 0.5
    finally:
        await client.client.aclose()
