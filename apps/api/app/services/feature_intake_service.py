# ############################################################################
# AI_HEADER: MODULE_FEATURE_INTAKE_SERVICE
# ROLE: Feature creation and intake orchestration
# DEPENDENCIES: sqlalchemy, app.db.models, app.schemas.feature
# GRACE_ANCHORS: [FEATURE_INTAKE_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-FEATURE-INTAKE-SERVICE
# purpose: Validate input, create Feature row, create initial planning runs,
#   and enqueue background planning task. Emit feature-level events.
# owns:
#   - apps/api/app/services/feature_intake_service.py
# inputs:
#   - FeatureCreateRequest (title, description, target_repo_root, mode, origin, self_improvement)
#   - AsyncSession for DB persistence
# outputs:
#   - FeatureCreateResult with feature_id, status, and planning state
# dependencies:
#   - M-DB-MODELS (Feature, FeaturePlanningRun)
#   - M-DB-SESSION (AsyncSession)
#   - M-FEATURE-SCHEMA (FeatureCreateRequest, FeatureCreateResponse)
# side_effects:
#   - creates Feature row in database
#   - creates initial FeaturePlanningRun rows
#   - emits feature_submitted and planning_started events
# invariants:
#   - feature id is prefixed with "feat_"
#   - initial status is PLANNING for draft_plan mode (unless auto_queue goes directly)
#   - each planning run id is prefixed with "fpr_"
# failure_policy:
#   - input validation errors surface as 422
#   - DB errors propagate to caller
# non_goals:
#   - no actual planning execution (delegated to FeaturePlanningService)
# END_MODULE_CONTRACT: M-FEATURE-INTAKE-SERVICE

# START_MODULE_MAP: M-FEATURE-INTAKE-SERVICE
# public_entrypoints:
#   - FeatureIntakeService.create_feature
# semantic_blocks:
#   - FEATURE_INTAKE_SERVICE: feature creation orchestration
# owned_tests:
#   - tests/api/test_features_create_business.py
# END_MODULE_MAP: M-FEATURE-INTAKE-SERVICE

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_event, bind_log_context
from app.db.models import Feature, FeaturePlanningRun
from app.schemas.feature import (
    FeatureCreateRequest,
    FeatureCreateResponse,
    PlanningRun as PlanningRunSchema,
    PlanningState,
)


class FeatureIntakeService:
    """Orchestrate feature creation and initial planning lifecycle."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_feature(
        self,
        request: FeatureCreateRequest,
        trace_id: str = "",
    ) -> FeatureCreateResponse:
        bind_log_context(module="M-FEATURE-INTAKE-SERVICE", block="FEATURE_INTAKE_SERVICE")

        feature_id = f"feat_{uuid.uuid4().hex[:24]}"
        now = datetime.now(timezone.utc)

        feature = Feature(
            id=feature_id,
            title=request.title,
            description=request.description,
            target_repo_root=request.target_repo_root,
            status="PLANNING",
            mode=request.mode,
            origin=request.origin,
            self_improvement=request.self_improvement,
            spec_json=json.dumps({
                "title": request.title,
                "description": request.description,
                "target_repo_root": request.target_repo_root,
                "mode": request.mode,
                "origin": request.origin,
            }),
        )
        self.db.add(feature)

        run_id = f"fpr_{uuid.uuid4().hex[:24]}"
        planning_run = FeaturePlanningRun(
            id=run_id,
            feature_id=feature_id,
            stage="submit",
            status="done",
            started_at=now,
            finished_at=now,
            duration_ms=0,
            executor_id="feature_intake",
            trace_id=trace_id,
        )
        self.db.add(planning_run)

        # Create pending context_builder run
        cb_run_id = f"fpr_{uuid.uuid4().hex[:24]}"
        cb_run = FeaturePlanningRun(
            id=cb_run_id,
            feature_id=feature_id,
            stage="context_builder",
            status="pending",
            executor_id="context_collector",
            trace_id=trace_id,
        )
        self.db.add(cb_run)

        await self.db.commit()
        await self.db.refresh(feature)

        log_event(
            "feature_submitted",
            level="info",
            msg=f"Feature {feature_id} created: {request.title}",
            payload={
                "feature_id": feature_id,
                "mode": request.mode,
                "origin": request.origin,
                "title": request.title,
            },
        )

        log_event(
            "planning_started",
            level="info",
            msg=f"Planning started for feature {feature_id}",
            payload={
                "feature_id": feature_id,
                "current_stage": "context_builder",
            },
        )

        return FeatureCreateResponse(
            feature_id=feature_id,
            status="PLANNING",
            mode=request.mode,
            planning=PlanningState(
                feature_id=feature_id,
                status="PLANNING",
                current_stage="context_builder",
                runs=[
                    PlanningRunSchema(
                        id=run_id,
                        stage="submit",
                        status="done",
                        started_at=now,
                        finished_at=now,
                        duration_ms=0,
                        executor_id="feature_intake",
                    ),
                    PlanningRunSchema(
                        id=cb_run_id,
                        stage="context_builder",
                        status="pending",
                        executor_id="context_collector",
                    ),
                ],
            ),
        )
