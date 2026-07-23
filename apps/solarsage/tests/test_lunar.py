# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_LUNAR
# ROLE: Unit & integration tests for sidecar /v1/lunar-window endpoint and LunarService
# DEPENDENCIES: pytest, httpx
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for lunar window calculations, phase angles, VOC, sign ingresses.
# owns:
#   - apps/solarsage/tests/test_lunar.py
# inputs: date ranges
# outputs: assertions on phase_angle, moon_sign, VOC intervals
# END_MODULE_CONTRACT

from datetime import date
import pytest
from httpx import AsyncClient, ASGITransport

from solarsage.app import app
from solarsage.services.lunar import LunarService

pytestmark = pytest.mark.usefixtures("moshier_mode")


@pytest.mark.asyncio
async def test_lunar_window_endpoint() -> None:
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.post(
            "/v1/lunar-window",
            json={"from_date": "2026-08-01", "to_date": "2026-08-03"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "days" in data
        assert len(data["days"]) == 3

        day1 = data["days"][0]
        assert day1["date"] == "2026-08-01"
        assert "moon_sign" in day1
        assert "moon_sign_ru" in day1
        assert "phase_angle" in day1
        assert "waxing" in day1
        assert "illumination" in day1
        assert "is_voc_noon" in day1
        assert "voc_intervals" in day1
        assert "voc_fraction" in day1
        assert "mercury_retro" in day1


def test_lunar_phase_new_and_full_moon() -> None:
    service = LunarService()
    # Solar eclipse / New Moon: 2026-08-12
    new_moon_info = service.compute_day(date(2026, 8, 12))
    # Phase angle near 0° or 360° (within 10° tolerance)
    assert new_moon_info.phase_angle < 15.0 or new_moon_info.phase_angle > 345.0
    assert new_moon_info.illumination < 0.1

    # Full Moon: 2026-08-28
    full_moon_info = service.compute_day(date(2026, 8, 28))
    # Phase angle near 180° (within 15° tolerance)
    assert abs(full_moon_info.phase_angle - 180.0) < 15.0
    assert full_moon_info.illumination > 0.9


def test_lunar_voc_regression_not_always_voc() -> None:
    """Regression (2026-07-23): without swe.FLG_SPEED every calc_ut returned
    speed=0.0, rel_speed<=0 skipped all planets, and every day read as VOC
    (voc_fraction == 1.0). VOC must vary over a window."""
    service = LunarService()
    days = service.compute_window(date(2026, 8, 1), date(2026, 8, 10))
    fracs = [d.voc_fraction for d in days]
    assert not all(f == 1.0 for f in fracs), "all days VOC 1.0 — aspect detection broken (FLG_SPEED?)"
    assert any(f == 0.0 for f in fracs)
    assert any(0.0 < f < 1.0 for f in fracs)


def test_lunar_mercury_retro_real_speed() -> None:
    """Regression: mercury_retro must come from a real speed reading.
    Mercury was retrograde 2026-06-30..2026-07-23 (Swiss Ephemeris)."""
    service = LunarService()
    assert service.compute_day(date(2026, 7, 15)).mercury_retro is True
    assert service.compute_day(date(2026, 8, 1)).mercury_retro is False
