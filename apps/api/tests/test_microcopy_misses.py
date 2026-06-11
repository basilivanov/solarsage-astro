# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

# ############################################################################
# AI_HEADER: MODULE_TEST_MICROCOPY_MISSES
# ROLE: Tests for microcopy miss tracking (W-9.2)
# DEPENDENCIES: pytest, httpx, app.services.microcopy_service
# GRACE_ANCHORS: [TEST_TRACK_MISS, TEST_INCREMENT_HIT_COUNT, TEST_WEEKLY_REPORT_ENDPOINT]
# WAVE: W-9.2
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-MICROCOPY-MISSES
# purpose: Verify microcopy miss tracking and weekly report functionality.
# owns:
#   - apps/api/tests/test_microcopy_misses.py
# inputs:
#   - db_session: AsyncSession fixture
#   - async_client: AsyncClient fixture
# outputs:
#   - test results (pass/fail)
# dependencies:
#   - M-MICROCOPY-SERVICE
#   - M-API-MICROCOPY
# side_effects:
#   - writes to test database
# invariants:
#   - missing keys are tracked
#   - hit_count increments on repeated misses
#   - weekly report returns correct data
# failure_policy:
#   - tests fail on assertion errors
# non_goals:
#   - no integration with real dictionary
# END_MODULE_CONTRACT: M-TEST-MICROCOPY-MISSES

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.microcopy_service import MicrocopyService


@pytest.mark.asyncio
async def test_microcopy_tracks_miss(db_session: AsyncSession):
    """Missing key is tracked in database. W-9.2."""
    service = MicrocopyService(db_session)

    # Get missing key
    result = await service.get("missing.key", context="test")

    assert result == "[missing.key]"

    # Check tracked
    report = await service.get_weekly_report()
    assert len(report) == 1
    assert report[0]["key"] == "missing.key"
    assert report[0]["hit_count"] == 1


@pytest.mark.asyncio
async def test_microcopy_increments_hit_count(db_session: AsyncSession):
    """Repeated miss increments hit_count. W-9.2."""
    service = MicrocopyService(db_session)

    # Get same missing key twice
    await service.get("missing.key")
    await service.get("missing.key")

    # Check hit_count
    report = await service.get_weekly_report()
    assert len(report) == 1
    assert report[0]["hit_count"] == 2


@pytest.mark.asyncio
async def test_weekly_report_endpoint(async_client: AsyncClient, make_initdata, db_session):
    """Weekly report endpoint returns misses. W-9.2."""
    # Auth (admin endpoint, simplified for MVP)
    user_raw = make_initdata(user_id=11111, username="admin")
    await async_client.post("/api/auth/telegram", json={"initData": user_raw})

    # Create a miss
    service = MicrocopyService(db_session)
    await service.get("test.missing.key")

    # Get report
    response = await async_client.get("/api/admin/microcopy/misses")
    assert response.status_code == 200

    data = response.json()
    assert len(data["misses"]) == 1
    assert data["misses"][0]["key"] == "test.missing.key"


@pytest.mark.asyncio
async def test_microcopy_returns_existing_key(db_session: AsyncSession):
    """Existing key returns value without tracking. W-9.1."""
    service = MicrocopyService(db_session)

    # Get existing key
    result = await service.get("day.supportive.headline")

    assert result == "День возможностей"

    # Check not tracked
    report = await service.get_weekly_report()
    assert len(report) == 0
