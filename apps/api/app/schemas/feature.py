# ############################################################################
# AI_HEADER: MODULE_FEATURE_SCHEMA
# ROLE: Feature intake and planning Pydantic schemas
# DEPENDENCIES: pydantic, datetime
# GRACE_ANCHORS: [FEATURE_SCHEMAS]
# ############################################################################

# START_MODULE_CONTRACT: M-FEATURE-SCHEMA
# purpose: Define FeatureCreateRequest, FeatureCreateResponse, PlanningRun,
#   FeaturePlanningState, and ApprovePlanResponse Pydantic schemas.
# owns:
#   - apps/api/app/schemas/feature.py
# inputs:
#   - none (type definitions)
# outputs:
#   - FeatureCreateRequest, FeatureCreateResponse, PlanningRun,
#     FeaturePlanningState, ApprovePlanResponse
# dependencies:
#   - pydantic
# side_effects:
#   - none (type-only module)
# END_MODULE_CONTRACT: M-FEATURE-SCHEMA

# START_MODULE_MAP: M-FEATURE-SCHEMA
# public_entrypoints:
#   - FeatureCreateRequest
#   - FeatureCreateResponse
#   - PlanningRun
#   - FeaturePlanningState
#   - ApprovePlanResponse
# semantic_blocks:
#   - FEATURE_SCHEMAS: Pydantic models for feature endpoints
# END_MODULE_MAP: M-FEATURE-SCHEMA

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.schemas._base import CamelModel


class FeatureCreateRequest(CamelModel):
    """Request body for POST /api/features."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str | None = Field(None)
    target_repo_root: str | None = Field(None)
    mode: str = Field("draft_plan")
    origin: str = Field("business")
    self_improvement: bool = Field(False)


class PlanningRun(CamelModel):
    """Single planning run stage visible in GET /api/features/{id}/planning."""

    id: str
    stage: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    duration_ms: int | None = None
    executor_id: str | None = None
    model: str | None = None
    stdout_path: str | None = None
    stderr_path: str | None = None
    error: str | None = None


class PlanningState(CamelModel):
    """Planning state returned from GET /api/features/{id}/planning."""

    feature_id: str
    status: str
    current_stage: str | None = None
    plan_json: dict[str, Any] | None = None
    runs: list[PlanningRun] = Field(default_factory=list)


class FeatureCreateResponse(CamelModel):
    """Response from POST /api/features."""

    feature_id: str
    status: str
    mode: str
    planning: PlanningState | None = None


class ApprovePlanResponse(CamelModel):
    """Response from POST /api/features/{id}/approve-plan."""

    feature_id: str
    status: str
    waves_count: int = 0
    packets_count: int = 0
    packet_ids: list[str] = Field(default_factory=list)


class FeatureListItem(CamelModel):
    """Single feature in admin feature list."""

    id: str
    title: str
    status: str
    mode: str
    origin: str
    created_at: datetime
    updated_at: datetime
    planning_runs_count: int = 0
    current_stage: str | None = None
