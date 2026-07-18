# ############################################################################
# AI_HEADER: MODULE_DAY_SCORING_RUNTIME_SERVICE — shared V1/V2 dual-run scorer.
# ROLE: Shared runtime scorer for TodayService and CalendarService.
#       Handles feature flags, dual-run, V2 shadow mode, and diff logging.
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-SCORING-RUNTIME-SERVICE
# purpose: Compute V1 scoring and optionally V2 scoring while selecting exactly
#          one result from global flags plus an explicit request-scoped override.
# owns:
#   - apps/api/app/services/day_scoring_runtime_service.py
# inputs: day signals, optional activation layer/request metadata, global rollout
#         flags, and optional force_v2 request authority.
# outputs: selected scoring version/result plus V1, optional V2, diff, and error.
# dependencies: settings, scoring services, activation/normalization schemas,
#               version constants, and existing structured logging helpers.
# side_effects: emits existing scoring.v2_diff logs when V2 is computed.
# emitted_logs: scoring.v2_diff.
# invariants:
#   - V1 is always computed.
#   - force_v2 can select V2 but cannot disable globally selected V2.
#   - Dual-run alone computes V2 without selecting it.
#   - Rollout flags are snapshotted once per compute call.
# failure_policy: selected V2 errors are raised; shadow-only V2 errors are
#                 recorded while V1 remains selected.
# END_MODULE_CONTRACT: M-DAY-SCORING-RUNTIME-SERVICE

# START_MODULE_MAP: M-DAY-SCORING-RUNTIME-SERVICE
# public_entrypoints:
#   - should_compute_v2
#   - selected_scoring_version_for_flags
#   - DualRunResult
#   - DayScoringRuntimeService.compute
# semantic_blocks:
#   - FLAG_SELECTION: compatible selection and compute helpers.
#   - RESULT_CONTRACT: runtime result value.
#   - RUNTIME_COMPUTE: snapshot-driven V1/V2 computation and selection.
# owned_tests:
#   - apps/api/tests/test_scoring_v2_runtime_flags.py
#   - apps/api/tests/test_today_selection_context.py
# END_MODULE_MAP: M-DAY-SCORING-RUNTIME-SERVICE

from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from app.core.config import settings
from app.core.logging import log_block, log_event
from app.core.versions import LEGACY_SCORING_VERSION, SCORING_V2_VERSION
from app.schemas.activation import ActivationLayer
from app.schemas.normalization import AstroSignal
from app.services.scoring_service import ScoringService
from app.services.scoring_v2_service import ScoringV2Service


# START_BLOCK: FLAG_SELECTION
def should_compute_v2(*, force_v2: bool = False) -> bool:
    # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.should_compute_v2
    # purpose: Decide whether V2 must compute for selection or shadow dual-run.
    # inputs: force_v2 — explicit request-scoped selection authority.
    # returns: true when V2 is selected or the global dual-run flag is enabled.
    # side_effects: reads global V2 selection and dual-run flags.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.should_compute_v2
    """Return whether V2 computation is selected or needed for dual-run."""
    v2_selected = bool(force_v2 or settings.solarsage_v2_enabled)
    return v2_selected or bool(settings.solarsage_v2_dual_run)


def selected_scoring_version_for_flags(*, force_v2: bool = False) -> int | str:
    # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.selected_scoring_version_for_flags
    # purpose: Select the scoring version from explicit request authority and
    #          the global V2 enablement flag, excluding compute-only dual-run.
    # inputs: force_v2 — explicit request-scoped selection authority.
    # returns: canonical current V2 version when selected, otherwise legacy V1.
    # side_effects: reads the global V2 selection flag.
    # emitted_logs: none.
    # error_behavior: none.
    # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.selected_scoring_version_for_flags
    """Return the selected version without treating dual-run as selection."""
    v2_selected = bool(force_v2 or settings.solarsage_v2_enabled)
    return SCORING_V2_VERSION if v2_selected else LEGACY_SCORING_VERSION
# END_BLOCK: FLAG_SELECTION


# START_BLOCK: RESULT_CONTRACT
@dataclass
class DualRunResult:
    """Result of a dual-run V1/V2 scoring computation."""

    selected_result: dict[str, Any]  # V1-shaped dict for existing services
    selected_scoring_version: int | str  # 1 for V1, SCORING_V2_VERSION for V2
    v1_result: dict[str, Any]
    v2_result: Any | None = None
    diff: dict[str, Any] | None = None
    v2_error: str | None = None
# END_BLOCK: RESULT_CONTRACT


# START_BLOCK: RUNTIME_COMPUTE
class DayScoringRuntimeService:
    """Shared runtime scorer with global and request-scoped V2 selection."""

    def compute(
        self,
        day_signals: list[AstroSignal],
        activation_layer: ActivationLayer | None = None,
        user_id: UUID | None = None,
        target_date: str | None = None,
        *,
        force_v2: bool = False,
    ) -> DualRunResult:
        # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.compute
        # purpose: Compute V1 and optional V2 from one request-local flag snapshot.
        # inputs: day_signals, activation_layer, user_id, target_date, and
        #         force_v2 explicit request-scoped selection authority.
        # returns: DualRunResult with selected, v1, and optional v2/diff/error
        # side_effects: emits existing scoring.v2_diff logs when V2 computes.
        # emitted_logs: scoring.v2_diff.
        # error_behavior: raises selected V2 failures; records shadow-only failures.
        # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-RUNTIME-SERVICE.compute
        v1_service = ScoringService()
        v2_service = ScoringV2Service()

        v2_selected = bool(force_v2 or settings.solarsage_v2_enabled)
        v2_dual_run = bool(settings.solarsage_v2_dual_run)
        compute_v2 = v2_selected or v2_dual_run

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
                            "date": target_date,
                            "selected_version": SCORING_V2_VERSION if v2_selected else LEGACY_SCORING_VERSION,
                            "v1_day_status": v1_day_status,
                            "v2_day_status": v2_result.day_status,
                            "sphere_diffs": sphere_diffs,
                        },
                    )

            except Exception as e:
                v2_error = str(e)
                if v2_selected:
                    raise  # Fail loudly whenever V2 is selected.
                # In dual-run mode, silently record the error
                with log_block(slice="W-DAY", module="M-TODAY-SERVICE", block="V2_DUAL_RUN"):
                    log_event(
                        "scoring.v2_diff",
                        level="warning",
                        msg="V2 dual-run scoring failed",
                        payload={
                            "date": target_date,
                        },
                        error={
                            "kind": type(e).__name__,
                        },
                    )

        # Select result
        selected_scoring_version: int | str
        if v2_selected and v2_result is not None:
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
# END_BLOCK: RUNTIME_COMPUTE
