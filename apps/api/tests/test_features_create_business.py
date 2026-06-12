
# ############################################################################
# AI_HEADER: MODULE_TESTS_FEATURES_CREATE
# ROLE: Tests for POST /api/features business intake
# DEPENDENCIES: app.api.features, app.services.feature_intake_service
# GRACE_ANCHORS: [FEATURE_CREATE_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-FEATURES-CREATE
# purpose: Verify POST /api/features creates Feature with PLANNING status and
#   returns correct planning state.
# owns:
#   - tests/api/test_features_create_business.py
# inputs:
#   - HTTP requests to /api/features
# outputs:
#   - assertion results
# dependencies:
#   - M-API-FEATURES
#   - M-DB-MODELS
#   - M-DB-SESSION
# side_effects:
#   - creates Feature rows in test DB
# invariants:
#   - create in draft_plan mode returns PLANNING status
#   - create in auto_queue mode completes full pipeline
# failure_policy:
#   - N/A (tests)
# END_MODULE_CONTRACT: M-TESTS-FEATURES-CREATE

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


@pytest.mark.asyncio
async def test_create_feature_requires_session(async_client: AsyncClient) -> None:
    """POST /api/features returns 401 without auth."""
    r = await async_client.post(
        "/api/features",
        json={"title": "Test feature"},
    )
    assert r.status_code == 401


@pytest.mark.asyncio
async def test_create_feature_draft_plan(
    async_client: AsyncClient,
    make_initdata,
    db_session: AsyncSession,
) -> None:
    """Create feature in draft_plan mode returns PLANNING."""
    await _login(async_client, make_initdata)

    r = await async_client.post(
        "/api/features",
        json={
            "title": "Add dark mode",
            "description": "Add dark mode toggle to settings",
            "mode": "draft_plan",
            "origin": "business",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]

    assert data["status"] == "PLANNING"
    assert data["mode"] == "draft_plan"
    assert data["feature_id"].startswith("feat_")
    assert data["planning"]["current_stage"] == "context_builder"
    assert len(data["planning"]["runs"]) == 2

    # Verify DB
    result = await db_session.execute(
        select(Feature).where(Feature.id == data["feature_id"])
    )
    feature = result.scalar_one_or_none()
    assert feature is not None
    assert feature.title == "Add dark mode"
    assert feature.status == "PLANNING"
    assert feature.mode == "draft_plan"
    assert feature.origin == "business"

    runs_result = await db_session.execute(
        select(FeaturePlanningRun).where(
            FeaturePlanningRun.feature_id == data["feature_id"]
        )
    )
    runs = runs_result.scalars().all()
    assert len(runs) == 2
    stages = {r.stage for r in runs}
    assert stages == {"submit", "context_builder"}


@pytest.mark.asyncio
async def test_create_feature_auto_queue(
    async_client: AsyncClient,
    make_initdata,
    db_session: AsyncSession,
) -> None:
    """Create feature in auto_queue mode completes pipeline -> QUEUED."""
    await _login(async_client, make_initdata)

    r = await async_client.post(
        "/api/features",
        json={
            "title": "Auto feature",
            "mode": "auto_queue",
            "origin": "business",
        },
    )
    assert r.status_code == 200, r.text
    body = r.json()
    data = body["data"]

    assert data["status"] == "QUEUED"

    # Verify DB
    result = await db_session.execute(
        select(Feature).where(Feature.id == data["feature_id"])
    )
    feature = result.scalar_one_or_none()
    assert feature is not None
    assert feature.status == "QUEUED"

    runs_result = await db_session.execute(
        select(FeaturePlanningRun).where(
            FeaturePlanningRun.feature_id == data["feature_id"]
        )
    )
    runs = runs_result.scalars().all()
    stages = {r.stage for r in runs}
    assert stages == {"submit", "context_builder", "architect", "materialize"}


@pytest.mark.asyncio
async def test_create_feature_default_mode(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Default mode is draft_plan."""
    await _login(async_client, make_initdata)

    r = await async_client.post(
        "/api/features",
        json={"title": "Default mode feature"},
    )
    assert r.status_code == 200, r.text
    data = r.json()["data"]
    assert data["mode"] == "draft_plan"
    assert data["status"] == "PLANNING"


@pytest.mark.asyncio
async def test_create_feature_validates_title(
    async_client: AsyncClient,
    make_initdata,
) -> None:
    """Empty title returns 422."""
    await _login(async_client, make_initdata)

    r = await async_client.post(
        "/api/features",
        json={"title": ""},
    )
    assert r.status_code == 422
