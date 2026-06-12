# ############################################################################
# AI_HEADER: MODULE_API_FEATURES
# ROLE: Feature intake and planning API endpoints
# DEPENDENCIES: fastapi, sqlalchemy, app.services.feature_*
# GRACE_ANCHORS: [CREATE_FEATURE_ENDPOINT, PLANNING_ENDPOINT, APPROVE_PLAN_ENDPOINT, REGENERATE_PLAN_ENDPOINT]
# ############################################################################

# START_MODULE_CONTRACT: M-API-FEATURES
# purpose: Feature intake and planning API — create business features, get
#   planning state, approve/reject/regenerate plans. Router is thin;
#   orchestration logic lives in service layer.
# owns:
#   - apps/api/app/api/features.py
# inputs:
#   - POST /api/features: FeatureCreateRequest
#   - GET /api/features/{feature_id}/planning: feature_id path param
#   - POST /api/features/{feature_id}/approve-plan: feature_id path param
#   - POST /api/features/{feature_id}/regenerate-plan: feature_id path param
# outputs:
#   - FeatureCreateResponse
#   - FeaturePlanningState
#   - ApprovePlanResponse
# dependencies:
#   - M-FEATURE-INTAKE-SERVICE
#   - M-FEATURE-PLANNING-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES
# side_effects:
#   - creates/updates Feature and FeaturePlanningRun rows
#   - emits feature-level events
# invariants:
#   - all endpoints require authentication
#   - approve-plan only allowed when Feature.status == PLAN_READY
#   - regenerate-plan only allowed when PLAN_READY or PLAN_FAILED
# failure_policy:
#   - 404 on unknown feature_id
#   - 409 on invalid status transition
#   - 400 on validation errors
# non_goals:
#   - no SSE/WebSocket (Wave 2+)
#   - no direct LLM calls in router
# END_MODULE_CONTRACT: M-API-FEATURES

# START_MODULE_MAP: M-API-FEATURES
# public_entrypoints:
#   - create_feature (POST /api/features)
#   - get_planning_state (GET /api/features/{feature_id}/planning)
#   - approve_plan (POST /api/features/{feature_id}/approve-plan)
#   - regenerate_plan (POST /api/features/{feature_id}/regenerate-plan)
# semantic_blocks:
#   - CREATE_FEATURE_ENDPOINT
#   - PLANNING_ENDPOINT
#   - APPROVE_PLAN_ENDPOINT
#   - REGENERATE_PLAN_ENDPOINT
# owned_tests:
#   - tests/api/test_features_create_business.py
#   - tests/api/test_feature_planning_api.py
# END_MODULE_MAP: M-API-FEATURES

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.db.models import User
from app.db.session import get_session
from sqlalchemy import select, func as sa_func

from app.db.models import Feature, FeaturePlanningRun
from app.schemas.feature import (
    ApprovePlanResponse,
    FeatureCreateRequest,
    FeatureCreateResponse,
    FeatureListItem,
    PlanningState,
)
from app.services.feature_intake_service import FeatureIntakeService
from app.services.feature_planning_service import FeaturePlanningService
from app.schemas.feature import PlanningRun as PlanningRunSchema

router = APIRouter()


# START_BLOCK: CREATE_FEATURE_ENDPOINT
@router.post("/api/features", response_model=dict)
async def create_feature(
    request: FeatureCreateRequest,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Create a new business feature and start planning pipeline."""
    intake_service = FeatureIntakeService(db)
    result = await intake_service.create_feature(request)

    if request.mode == "auto_queue":
        planning_service = FeaturePlanningService(db)
        try:
            context = await planning_service.run_context_builder(result.feature_id)
            await planning_service.run_architect(result.feature_id, context)
            approval = await planning_service.approve_plan(result.feature_id)
            return {
                "data": {
                    "feature_id": result.feature_id,
                    "status": approval.status,
                    "mode": request.mode,
                    "planning": None,
                }
            }
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            )

    return {"data": result.model_dump(mode="json")}
# END_BLOCK: CREATE_FEATURE_ENDPOINT


# START_BLOCK: PLANNING_ENDPOINT
@router.get("/api/features/{feature_id}/planning", response_model=dict)
async def get_planning_state(
    feature_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Get planning state with all runs for a feature."""
    planning_service = FeaturePlanningService(db)
    try:
        state = await planning_service.get_planning_state(feature_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )
    return {"data": state.model_dump(mode="json")}
# END_BLOCK: PLANNING_ENDPOINT


# START_BLOCK: APPROVE_PLAN_ENDPOINT
@router.post("/api/features/{feature_id}/approve-plan", response_model=dict)
async def approve_plan(
    feature_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Approve a PLAN_READY feature and materialize waves/packets."""
    planning_service = FeaturePlanningService(db)
    try:
        result = await planning_service.approve_plan(feature_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )
    return {"data": result.model_dump(mode="json")}
# END_BLOCK: APPROVE_PLAN_ENDPOINT


# START_BLOCK: REGENERATE_PLAN_ENDPOINT
@router.post("/api/features/{feature_id}/regenerate-plan", response_model=dict)
async def regenerate_plan(
    feature_id: str,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Regenerate plan for a PLAN_READY or PLAN_FAILED feature."""
    planning_service = FeaturePlanningService(db)
    try:
        state = await planning_service.regenerate_plan(feature_id)
    except ValueError as exc:
        msg = str(exc)
        if "not found" in msg.lower():
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=msg,
            )
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=msg,
        )
    return {"data": state.model_dump(mode="json")}
# END_BLOCK: REGENERATE_PLAN_ENDPOINT


# START_BLOCK: LIST_FEATURES_ENDPOINT
@router.get("/api/admin/features", response_model=dict)
async def list_features(
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
    limit: int = 50,
    offset: int = 0,
    status_filter: str | None = None,
):
    """List features for admin dashboard."""
    query = select(Feature).order_by(Feature.created_at.desc()).limit(limit).offset(offset)
    if status_filter:
        query = query.where(Feature.status == status_filter)

    result = await db.execute(query)
    features = result.scalars().all()

    items = []
    for f in features:
        runs_count_query = select(sa_func.count()).select_from(FeaturePlanningRun).where(
            FeaturePlanningRun.feature_id == f.id
        )
        count_result = await db.execute(runs_count_query)
        runs_count = count_result.scalar() or 0

        items.append(FeatureListItem(
            id=f.id,
            title=f.title,
            status=f.status,
            mode=f.mode,
            origin=f.origin,
            created_at=f.created_at,
            updated_at=f.updated_at,
            planning_runs_count=runs_count,
        ))

    return {"data": [item.model_dump(mode="json") for item in items]}
# END_BLOCK: LIST_FEATURES_ENDPOINT


# START_BLOCK: PLANNING_LOGS_ENDPOINT
@router.get("/api/features/{feature_id}/planning/{run_id}/logs", response_model=dict)
async def get_planning_logs(
    feature_id: str,
    run_id: str,
    stream: str = "stdout",
    tail: int = 200,
    db: AsyncSession = Depends(get_session),
    user: User = Depends(require_session),
):
    """Get planning run logs (stdout/stderr)."""
    planning_service = FeaturePlanningService(db)
    try:
        state = await planning_service.get_planning_state(feature_id)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    run = next((r for r in state.runs if r.id == run_id), None)
    if not run:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Run not found: {run_id}",
        )

    path_str = run.stdout_path if stream == "stdout" else run.stderr_path
    if not path_str:
        return {
            "lines": [],
            "total": 0,
            "source_file": None,
            "truncated": False,
        }

    import os
    path = path_str
    if not os.path.exists(path):
        return {
            "lines": [],
            "total": 0,
            "source_file": path,
            "truncated": False,
        }

    tail = min(tail, 10000)
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        all_lines = f.readlines()
        total = len(all_lines)
        lines = all_lines[-tail:]

    return {
        "lines": lines,
        "total": total,
        "source_file": path,
        "truncated": total > tail,
    }
# END_BLOCK: PLANNING_LOGS_ENDPOINT
