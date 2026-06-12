
# ############################################################################
# AI_HEADER: MODULE_TESTS_FEATURE_PLANNING_API
# ROLE: Tests for feature planning endpoints
# DEPENDENCIES: app.api.features, app.services.feature_planning_service
# GRACE_ANCHORS: [FEATURE_PLANNING_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-FEATURE-PLANNING
# purpose: Verify GET /api/features/{id}/planning, POST approve-plan,
#   POST regenerate-plan behavior.
# owns:
#   - tests/api/test_feature_planning_api.py
# inputs:
#   - HTTP requests to feature planning endpoints
# outputs:
#   - assertion results
# dependencies:
#   - M-API-FEATURES
#   - M-DB-MODELS
#   - M-DB-SESSION
# side_effects:
#   - creates/updates Feature rows in test DB
# invariants:
#   - planning endpoint returns runs
#   - approve fails before PLAN_READY
# error_behavior:
#   - N/A (tests)
# END_MODULE_CONTRACT: M-TESTS-FEATURE-PLANNING

from __future__ import annotations

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Feature, FeaturePlanningRun


async def _login(async_client: AsyncClient, make_initdata, *, user_id: int = 42) -> None:
    raw = make_initdata(user_id=user_id, username="ada")
    r = await async_client.post("/api/auth/telegram", json={"initData": raw})
    assert r.status_code == 200, r.text


async def _create_feature(
    async_client: AsyncClient,
    title: str = "Test feature",
    mode: str = "draft_plan",
) -> str:
    r = await async_client.post(
        "/api/features",
        json={"title": title, "mode": mode},
    )
    assert r.status_code == 200, r.text
    return r.json()["data"]["feature_id"]


@pytest.mark.asyncio
async def test_get_planning_state_returns_runs(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Planning endpoint returns runs for a created feature."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client)

    r = await async_client.get(f"/api/features/{feature_id}/planning")
    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]

    assert data["feature_id"] == feature_id
    assert data["status"] == "PLANNING"
    assert data["current_stage"] == "context_builder"
    assert len(data["runs"]) == 2

    stages = {run["stage"] for run in data["runs"]}
    assert stages == {"submit", "context_builder"}


@pytest.mark.asyncio
async def test_get_planning_state_404(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Unknown feature returns 404."""
    await _login(async_client, make_initdata)

    r = await async_client.get("/api/features/feat_nonexistent/planning")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_approve_plan_fails_before_plan_ready(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Approve fails when feature is not PLAN_READY."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client)

    r = await async_client.post(f"/api/features/{feature_id}/approve-plan")
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_approve_plan_succeeds_after_plan_ready(
    async_client: AsyncClient,
    make_initdata,
    db_session: AsyncSession,
) -> None:
    """Approve succeeds after full planning pipeline."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client, mode="auto_queue")

    r_get = await async_client.get(f"/api/features/{feature_id}/planning")
    assert r_get.status_code == 200
    assert r_get.json()["data"]["status"] == "QUEUED"

    r_approve = await async_client.post(f"/api/features/{feature_id}/approve-plan")
    assert r_approve.status_code == 409, "Already QUEUED, should fail"


@pytest.mark.asyncio
async def test_approve_plan_materializes_waves(
    async_client: AsyncClient,
    make_initdata,
    db_session: AsyncSession,
) -> None:
    """Approve materializes plan into waves/packets."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client, mode="auto_queue")

    result = await db_session.execute(
        select(Feature).where(Feature.id == feature_id)
    )
    feature = result.scalar_one_or_none()
    assert feature is not None
    assert feature.status == "QUEUED"

    runs_result = await db_session.execute(
        select(FeaturePlanningRun)
        .where(FeaturePlanningRun.feature_id == feature_id)
        .where(FeaturePlanningRun.stage == "materialize")
    )
    materialize_run = runs_result.scalar_one_or_none()
    assert materialize_run is not None
    assert materialize_run.status == "done"


@pytest.mark.asyncio
async def test_regenerate_plan_fails_on_queued(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Regenerate fails for QUEUED features."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client, mode="auto_queue")

    r = await async_client.post(f"/api/features/{feature_id}/regenerate-plan")
    assert r.status_code == 409, r.text


@pytest.mark.asyncio
async def test_regenerate_plan_404(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Unknown feature returns 404."""
    await _login(async_client, make_initdata)

    r = await async_client.post("/api/features/feat_nonexistent/regenerate-plan")
    assert r.status_code == 404


@pytest.mark.asyncio
async def test_create_feature_minimal_payload(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Minimal payload (title only) creates feature successfully."""
    await _login(async_client, make_initdata)

    r = await async_client.post(
        "/api/features",
        json={"title": "Minimal"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["feature_id"].startswith("feat_")


@pytest.mark.asyncio
async def test_planning_state_lifecycle(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Planning state shows correct stages at each step."""
    await _login(async_client, make_initdata)
    feature_id = await _create_feature(async_client, mode="auto_queue")

    r = await async_client.get(f"/api/features/{feature_id}/planning")
    assert r.status_code == 200
    data = r.json()["data"]

    # After auto_queue, should be QUEUED
    assert data["status"] == "QUEUED"
    # Verify all 4 stages exist
    stages = {run["stage"] for run in data["runs"]}
    assert stages == {"submit", "context_builder", "architect", "materialize"}
    # All should be "done"
    for run in data["runs"]:
        assert run["status"] == "done"
