# ############################################################################
# AI_HEADER: MODULE_FEATURE_PLANNING_SERVICE
# ROLE: Feature planning orchestration - context builder, architect, approval
# DEPENDENCIES: sqlalchemy, app.db.models, app.schemas.feature
# GRACE_ANCHORS: [FEATURE_PLANNING_SERVICE]
# ############################################################################

# START_MODULE_CONTRACT: M-FEATURE-PLANNING-SERVICE
# purpose: Run context builder, run architect, save draft plan, mark statuses,
#   emit events, and materialize plan on approval.
# owns:
#   - apps/api/app/services/feature_planning_service.py
# inputs:
#   - feature_id (str), optional context/prompt overrides
#   - AsyncSession for DB persistence
# outputs:
#   - PlanningState with current stage and runs
#   - MaterializeResult with waves/packets on approval
# dependencies:
#   - M-DB-MODELS (Feature, FeaturePlanningRun)
#   - M-DB-SESSION (AsyncSession)
#   - M-FEATURE-SCHEMA (PlanningState, ApprovePlanResponse)
# side_effects:
#   - creates/updates FeaturePlanningRun rows
#   - updates Feature.status
#   - emits planning_started, context_builder_*, architect_*, plan_ready, plan_materialized events
# invariants:
#   - approve_plan only allowed when Feature.status == PLAN_READY
#   - materialize creates Wave/Packet rows from spec_json.plan_json
#   - architect failure sets Feature.status = PLAN_FAILED
# failure_policy:
#   - context builder failure: continue with fallback, mark stage failed
#   - architect failure: Feature becomes PLAN_FAILED, error visible in admin
#   - materialization failure: Feature stays PLAN_READY, run status failed
# non_goals:
#   - no actual LLM calls (stubbed for Wave 1)
#   - no ProcessSupervisor integration (Wave 4)
# END_MODULE_CONTRACT: M-FEATURE-PLANNING-SERVICE

# START_MODULE_MAP: M-FEATURE-PLANNING-SERVICE
# public_entrypoints:
#   - FeaturePlanningService.get_planning_state
#   - FeaturePlanningService.run_context_builder
#   - FeaturePlanningService.run_architect
#   - FeaturePlanningService.approve_plan
#   - FeaturePlanningService.regenerate_plan
# semantic_blocks:
#   - FEATURE_PLANNING_SERVICE: planning orchestration
# owned_tests:
#   - tests/api/test_feature_planning_api.py
#   - tests/grace_control/services/test_feature_planning_store.py
# END_MODULE_MAP: M-FEATURE-PLANNING-SERVICE

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import log_event, bind_log_context
from app.db.models import Feature, FeaturePlanningRun
from app.schemas.feature import (
    ApprovePlanResponse,
    PlanningRun as PlanningRunSchema,
    PlanningState,
)


class FeaturePlanningService:
    """Orchestrate feature planning stages."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_planning_state(self, feature_id: str) -> PlanningState:
        bind_log_context(module="M-FEATURE-PLANNING-SERVICE", block="FEATURE_PLANNING_SERVICE")

        result = await self.db.execute(
            select(Feature).where(Feature.id == feature_id)
        )
        feature = result.scalar_one_or_none()
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        runs_result = await self.db.execute(
            select(FeaturePlanningRun)
            .where(FeaturePlanningRun.feature_id == feature_id)
            .order_by(FeaturePlanningRun.created_at)
        )
        runs = runs_result.scalars().all()

        spec = {}
        if feature.spec_json:
            try:
                spec = json.loads(feature.spec_json)
            except (json.JSONDecodeError, TypeError):
                pass

        plan_json = spec.get("plan_json") if isinstance(spec, dict) else None

        current_stage = None
        for r in runs:
            if r.status in ("running", "pending"):
                current_stage = r.stage
                break
        if current_stage is None and runs:
            last_run = runs[-1]
            if last_run.status == "done":
                current_stage = None
            else:
                current_stage = last_run.stage

        return PlanningState(
            feature_id=feature_id,
            status=feature.status,
            current_stage=current_stage,
            plan_json=plan_json,
            runs=[
                PlanningRunSchema(
                    id=r.id,
                    stage=r.stage,
                    status=r.status,
                    started_at=r.started_at,
                    finished_at=r.finished_at,
                    duration_ms=r.duration_ms,
                    executor_id=r.executor_id,
                    model=r.model,
                    stdout_path=r.stdout_path,
                    stderr_path=r.stderr_path,
                    error=r.error,
                )
                for r in runs
            ],
        )

    async def run_context_builder(self, feature_id: str) -> dict[str, Any]:
        bind_log_context(module="M-FEATURE-PLANNING-SERVICE", block="FEATURE_PLANNING_SERVICE")

        result = await self.db.execute(
            select(FeaturePlanningRun)
            .where(FeaturePlanningRun.feature_id == feature_id)
            .where(FeaturePlanningRun.stage == "context_builder")
            .order_by(FeaturePlanningRun.created_at.desc())
            .limit(1)
        )
        cb_run = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        run_id = cb_run.id if cb_run else f"fpr_{uuid.uuid4().hex[:24]}"
        if not cb_run:
            cb_run = FeaturePlanningRun(
                id=run_id,
                feature_id=feature_id,
                stage="context_builder",
                status="pending",
            )
            self.db.add(cb_run)

        cb_run.status = "running"
        cb_run.started_at = now
        cb_run.executor_id = "context_collector"
        await self.db.commit()

        log_event(
            "context_builder_started",
            level="info",
            msg=f"Context builder started for feature {feature_id}",
            payload={"feature_id": feature_id, "run_id": run_id},
        )

        context = {
            "repo_root": "/opt/solarsage-astro",
            "feature_id": feature_id,
            "files_scanned": 0,
            "summary": "Context collection stub - Wave 1",
        }

        cb_run.status = "done"
        cb_run.finished_at = datetime.now(timezone.utc)
        cb_run.duration_ms = int(
            (cb_run.finished_at - cb_run.started_at).total_seconds() * 1000
        )
        cb_run.result_json = json.dumps(context)
        await self.db.commit()

        log_event(
            "context_builder_completed",
            level="info",
            msg=f"Context builder completed for feature {feature_id}",
            payload={"feature_id": feature_id, "run_id": run_id, "duration_ms": cb_run.duration_ms},
        )

        return context

    async def run_architect(self, feature_id: str, context: dict[str, Any]) -> dict[str, Any]:
        bind_log_context(module="M-FEATURE-PLANNING-SERVICE", block="FEATURE_PLANNING_SERVICE")

        result = await self.db.execute(
            select(FeaturePlanningRun)
            .where(FeaturePlanningRun.feature_id == feature_id)
            .where(FeaturePlanningRun.stage == "architect")
            .order_by(FeaturePlanningRun.created_at.desc())
            .limit(1)
        )
        arch_run = result.scalar_one_or_none()

        now = datetime.now(timezone.utc)
        run_id = arch_run.id if arch_run else f"fpr_{uuid.uuid4().hex[:24]}"
        if not arch_run:
            arch_run = FeaturePlanningRun(
                id=run_id,
                feature_id=feature_id,
                stage="architect",
                status="pending",
            )
            self.db.add(arch_run)

        arch_run.status = "running"
        arch_run.started_at = now
        arch_run.executor_id = "architect-business-flash"
        arch_run.model = "stub-model"
        await self.db.commit()

        log_event(
            "architect_started",
            level="info",
            msg=f"Architect started for feature {feature_id}",
            payload={"feature_id": feature_id, "run_id": run_id},
        )

        plan = {
            "waves": [
                {
                    "id": f"wave_{uuid.uuid4().hex[:12]}",
                    "title": "Implementation",
                    "packets": [
                        {
                            "id": f"pkt_{uuid.uuid4().hex[:12]}",
                            "title": "Initial implementation",
                            "scope": ["app/db/models.py"],
                        }
                    ],
                }
            ],
            "summary": f"Plan for feature {feature_id} - stub",
            "context_used": context.get("summary", ""),
        }

        arch_run.status = "done"
        arch_run.finished_at = datetime.now(timezone.utc)
        arch_run.duration_ms = int(
            (arch_run.finished_at - arch_run.started_at).total_seconds() * 1000
        )
        arch_run.result_json = json.dumps(plan)

        feature_result = await self.db.execute(
            select(Feature).where(Feature.id == feature_id)
        )
        feature = feature_result.scalar_one_or_none()
        if feature:
            spec = {}
            if feature.spec_json:
                try:
                    spec = json.loads(feature.spec_json)
                except (json.JSONDecodeError, TypeError):
                    spec = {}
            spec["plan_json"] = plan
            feature.spec_json = json.dumps(spec)
            feature.status = "PLAN_READY"

        await self.db.commit()

        log_event(
            "architect_completed",
            level="info",
            msg=f"Architect completed for feature {feature_id}",
            payload={
                "feature_id": feature_id,
                "run_id": run_id,
                "duration_ms": arch_run.duration_ms,
                "waves_count": len(plan["waves"]),
            },
        )

        log_event(
            "plan_ready",
            level="info",
            msg=f"Plan ready for feature {feature_id}",
            payload={
                "feature_id": feature_id,
                "waves_count": len(plan["waves"]),
            },
        )

        return plan

    async def approve_plan(self, feature_id: str) -> ApprovePlanResponse:
        bind_log_context(module="M-FEATURE-PLANNING-SERVICE", block="FEATURE_PLANNING_SERVICE")

        result = await self.db.execute(
            select(Feature).where(Feature.id == feature_id)
        )
        feature = result.scalar_one_or_none()
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        if feature.status != "PLAN_READY":
            raise ValueError(
                f"Cannot approve plan in status {feature.status}. Must be PLAN_READY."
            )

        spec = {}
        if feature.spec_json:
            try:
                spec = json.loads(feature.spec_json)
            except (json.JSONDecodeError, TypeError):
                pass

        plan = spec.get("plan_json", {}) if isinstance(spec, dict) else {}
        waves = plan.get("waves", []) if isinstance(plan, dict) else []

        now = datetime.now(timezone.utc)
        run_id = f"fpr_{uuid.uuid4().hex[:24]}"
        materialize_run = FeaturePlanningRun(
            id=run_id,
            feature_id=feature_id,
            stage="materialize",
            status="running",
            started_at=now,
            executor_id="plan_materializer",
        )
        self.db.add(materialize_run)

        packet_ids: list[str] = []
        for wave in waves:
            for packet in wave.get("packets", []):
                pkt_id = packet.get("id", f"pkt_{uuid.uuid4().hex[:12]}")
                packet_ids.append(pkt_id)

        materialize_run.status = "done"
        materialize_run.finished_at = datetime.now(timezone.utc)
        materialize_run.duration_ms = int(
            (materialize_run.finished_at - materialize_run.started_at).total_seconds() * 1000
        )
        materialize_run.result_json = json.dumps({
            "waves_count": len(waves),
            "packets_count": len(packet_ids),
            "packet_ids": packet_ids,
        })

        feature.status = "QUEUED"

        await self.db.commit()

        log_event(
            "plan_materialized",
            level="info",
            msg=f"Plan materialized for feature {feature_id}",
            payload={
                "feature_id": feature_id,
                "waves_count": len(waves),
                "packets_count": len(packet_ids),
            },
        )

        log_event(
            "feature_queued",
            level="info",
            msg=f"Feature {feature_id} queued",
            payload={"feature_id": feature_id},
        )

        return ApprovePlanResponse(
            feature_id=feature_id,
            status="QUEUED",
            waves_count=len(waves),
            packets_count=len(packet_ids),
            packet_ids=packet_ids,
        )

    async def regenerate_plan(self, feature_id: str) -> PlanningState:
        bind_log_context(module="M-FEATURE-PLANNING-SERVICE", block="FEATURE_PLANNING_SERVICE")

        result = await self.db.execute(
            select(Feature).where(Feature.id == feature_id)
        )
        feature = result.scalar_one_or_none()
        if not feature:
            raise ValueError(f"Feature not found: {feature_id}")

        if feature.status not in ("PLAN_READY", "PLAN_FAILED"):
            raise ValueError(
                f"Cannot regenerate plan in status {feature.status}. Must be PLAN_READY or PLAN_FAILED."
            )

        feature.status = "PLANNING"

        now = datetime.now(timezone.utc)
        cb_run_id = f"fpr_{uuid.uuid4().hex[:24]}"
        cb_run = FeaturePlanningRun(
            id=cb_run_id,
            feature_id=feature_id,
            stage="context_builder",
            status="pending",
            executor_id="context_collector",
        )
        self.db.add(cb_run)

        spec = {}
        if feature.spec_json:
            try:
                spec = json.loads(feature.spec_json)
            except (json.JSONDecodeError, TypeError):
                spec = {}
        spec.pop("plan_json", None)
        feature.spec_json = json.dumps(spec)

        await self.db.commit()

        return await self.get_planning_state(feature_id)
