# ############################################################################
# AI_HEADER: MODULE_DAY_SCORING_RUNTIME_SERVICE — shared V1/V2 dual-run scorer.
# ROLE: Shared runtime scorer for TodayService and CalendarService.
#       Handles feature flags, dual-run, V2 shadow mode, and diff logging.
# ############################################################################

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.logging import log_block, log_event
from app.core.versions import LEGACY_SCORING_VERSION, SCORING_V2_VERSION
from app.schemas.activation import ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.scoring_service import ScoringService
from app.services.scoring_v2_service import ScoringV2Service


def should_compute_v2() -> bool:
    """Return True if V2 computation may be needed (dual-run or enabled)."""
    return settings.solarsage_v2_enabled or settings.solarsage_v2_dual_run


def selected_scoring_version_for_flags() -> int | str:
    """Return the selected scoring version implied by feature flags.
    Used before cache read so V2-enabled does not read V1 cache."""
    return SCORING_V2_VERSION if settings.solarsage_v2_enabled else LEGACY_SCORING_VERSION


@dataclass
class DualRunResult:
    """Result of a dual-run V1/V2 scoring computation."""

    selected_result: dict[str, Any]  # V1-shaped dict for existing services
    selected_scoring_version: int | str  # 1 for V1, SCORING_V2_VERSION for V2
    v1_result: dict[str, Any]
    v2_result: Any | None = None
    diff: dict[str, Any] | None = None
    v2_error: str | None = None


class DayScoringRuntimeService:
    """Shared runtime scorer. Always computes V1. Computes V2 when
    SOLARSAGE_V2_DUAL_RUN or SOLARSAGE_V2_ENABLED is set."""

    def compute(
        self,
        day_signals: list[AstroSignal],
        activation_layer: ActivationLayer | None = None,
        user_id: UUID | None = None,
        target_date: str | None = None,
    ) -> DualRunResult:
        # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.compute
        # purpose: Compute dual-run scoring. Always V1, optionally V2.
        # inputs: day_signals, activation_layer, user_id, target_date
        # returns: DualRunResult with selected, v1, and optional v2/diff/error
        # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.compute
        v1_service = ScoringService()
        v2_service = ScoringV2Service()

        v2_enabled = settings.solarsage_v2_enabled
        v2_dual_run = settings.solarsage_v2_dual_run
        compute_v2 = v2_enabled or v2_dual_run

        # Always compute V1
        v1_result = v1_service.score_day(day_signals)
        v1_day_status = v1_result.get("day_status", "unknown")
        v1_sphere_scores = v1_result.get("sphere_scores", {})

        v2_result = None
        diff = None
        v2_error = None

        if compute_v2:
            try:
                v2_result = v2_service.score_day(day_signals, activation_layer)
                # Build diff
                v1_scores = {k: round(float(v), 4) for k, v in v1_sphere_scores.items()}
                v2_scores = {k: round(v.final_score, 4) for k, v in v2_result.sphere_scores.items()}
                all_keys = set(list(v1_scores.keys()) + list(v2_scores.keys()))
                sphere_diffs = {}
                for skey in sorted(all_keys):
                    v1_val = v1_scores.get(skey, 0.0)
                    v2_val = v2_scores.get(skey, 0.0)
                    delta = round(v2_val - v1_val, 4)
                    top_new = []
                    if delta > 0 and v2_result:
                        ss = v2_result.sphere_scores.get(skey)
                        if ss:
                            for c in ss.contributions:
                                if c.source == "activation" and c.amount > 0:
                                    top_new.append(c.source_id)
                                    if len(top_new) >= 3:
                                        break
                    sphere_diffs[skey] = {
                        "v1": v1_val,
                        "v2": v2_val,
                        "delta": delta,
                        "top_new_evidence": top_new,
                    }

                diff = {
                    "v1_day_status": v1_day_status,
                    "v2_day_status": v2_result.day_status,
                    "sphere_diffs": sphere_diffs,
                }

                # Log the diff
                with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="V2_DUAL_RUN"):
                    log_event(
                        "scoring.v2_diff",
                        level="info",
                        msg="V2 dual-run scoring diff",
                        payload={
                            "user_id": str(user_id) if user_id else None,
                            "date": target_date,
                            "selected_version": LEGACY_SCORING_VERSION if not v2_enabled else SCORING_V2_VERSION,
                            "v1_day_status": v1_day_status,
                            "v2_day_status": v2_result.day_status,
                            "sphere_diffs": sphere_diffs,
                        },
                    )

            except Exception as e:
                v2_error = str(e)
                if v2_enabled:
                    raise  # Fail loudly when V2 is enabled
                # In dual-run mode, silently record the error
                with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="V2_DUAL_RUN"):
                    log_event(
                        "scoring.v2_diff",
                        level="warning",
                        msg="V2 dual-run scoring failed",
                        payload={
                            "user_id": str(user_id) if user_id else None,
                            "date": target_date,
                            "error": str(e),
                        },
                    )

        # Select result
        if v2_enabled and v2_result is not None:
            selected_result = {
                "day_status": v2_result.day_status,
                "sphere_scores": {k: round(v.final_score, 4) for k, v in v2_result.sphere_scores.items()},
                "top_signals": v2_result.top_signals,
            }
            selected_scoring_version = SCORING_V2_VERSION
        else:
            selected_result = v1_result
            selected_scoring_version = LEGACY_SCORING_VERSION

        return DualRunResult(
            selected_result=selected_result,
            selected_scoring_version=selected_scoring_version,
            v1_result=v1_result,
            v2_result=v2_result,
            diff=diff,
            v2_error=v2_error,
        )
