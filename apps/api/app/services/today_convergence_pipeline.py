# ############################################################################
# AI_HEADER: MODULE_TODAY_CONVERGENCE_PIPELINE — pure W2 stage orchestration.
# ROLE: Composes the frozen canon, ledger, direct groups, tone, and presentation selector.
# ############################################################################

# START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PIPELINE
# purpose: Run the accepted W2 convergence stages in one deterministic pure entrypoint.
# owns:
#   - apps/api/app/services/today_convergence_pipeline.py
# inputs: RawPhysicalFact sequences, target date, IANA timezone, optional exact DayDelta keys, and frozen canon.
# outputs: immutable CanonicalPipelineBuilt or typed CanonicalPipelineUnavailable.
# dependencies: today_convergence_canon, today_convergence_ledger, today_convergence_groups, today_convergence_tone, today_convergence_selection.
# side_effects: reads frozen canon when omitted; never writes, logs, calls network, or persists.
# emitted_logs: none.
# invariants: stage order is canon → ledger → grouping → provisional tone → selection → tone rebind; tone selection cannot change public tone facts.
# failure_policy: only known typed stage errors become unavailable; arbitrary programming errors propagate.
# END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PIPELINE

# START_MODULE_MAP: M-TODAY-CONVERGENCE-PIPELINE
# public_entrypoints:
#   - CanonicalPipelineBuilt
#   - CanonicalPipelineUnavailable
#   - CanonicalPipelineResult
#   - run_canonical_today_pipeline
# semantic_blocks:
#   - ORCHESTRATION: accepted W2 stage composition and tone rebind.
#   - FAILURE_BOUNDARIES: typed unavailable results at the failing stage.
#   - IMMUTABLE_RESULTS: frozen public pipeline records without compatibility aliases.
# owned_tests:
#   - apps/api/tests/test_today_convergence_pipeline.py
# END_MODULE_MAP: M-TODAY-CONVERGENCE-PIPELINE

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal, Sequence

from app.services.today_convergence_canon import (
    TodayConvergenceCanon,
    TodayConvergenceCanonError,
    load_today_convergence_canon,
)
from app.services.today_convergence_groups import (
    CanonicalGroupingResult,
    TodayConvergenceGroupingError,
    build_canonical_groups,
)
from app.services.today_convergence_ledger import (
    CanonicalLedger,
    TodayConvergenceLedgerError,
    build_canonical_ledger,
)
from app.services.today_convergence_selection import (
    CanonicalSelectionResult,
    TodayConvergenceSelectionError,
    select_canonical_presentation,
)
from app.services.today_convergence_tone import (
    CanonicalToneResult,
    TodayConvergenceToneError,
    compute_canonical_tone,
)
from app.services.today_convergence_units import RawPhysicalFact


FailureStage = Literal["canon", "ledger", "grouping", "tone", "selection", "tone_rebind"]


@dataclass(frozen=True)
class CanonicalPipelineBuilt:
    """Immutable successful composition of the accepted W2 records."""

    formula_version: str
    state: Literal["convergence_today", "quiet_day"]
    ledger: CanonicalLedger
    grouping: CanonicalGroupingResult
    tone: CanonicalToneResult
    selection: CanonicalSelectionResult


@dataclass(frozen=True)
class CanonicalPipelineUnavailable:
    """Immutable typed failure with all successfully completed stage records."""

    formula_version: str | None
    state: Literal["unavailable"]
    failure_stage: FailureStage
    failure_reason: str
    ledger: CanonicalLedger | None
    grouping: CanonicalGroupingResult | None
    tone: CanonicalToneResult | None


CanonicalPipelineResult = CanonicalPipelineBuilt | CanonicalPipelineUnavailable


# START_BLOCK: FAILURE_BOUNDARIES
def _unavailable(
    *,
    canon: TodayConvergenceCanon | None,
    stage: FailureStage,
    error: Exception | str,
    ledger: CanonicalLedger | None = None,
    grouping: CanonicalGroupingResult | None = None,
    tone: CanonicalToneResult | None = None,
) -> CanonicalPipelineUnavailable:
    return CanonicalPipelineUnavailable(
        formula_version=None if canon is None else canon.formula_version,
        state="unavailable",
        failure_stage=stage,
        failure_reason=str(error),
        ledger=ledger,
        grouping=grouping,
        tone=tone,
    )


def _resolve_canon(canon: TodayConvergenceCanon | None) -> TodayConvergenceCanon:
    if canon is None:
        return load_today_convergence_canon()
    if not isinstance(canon, TodayConvergenceCanon):
        raise TodayConvergenceCanonError("today_convergence_canon:invalid_type")
    return canon


# END_BLOCK: FAILURE_BOUNDARIES


# START_BLOCK: TONE_REBIND
def _tone_facts_are_stable(before: CanonicalToneResult, after: CanonicalToneResult) -> bool:
    return (
        before.tone_policy_version == after.tone_policy_version
        and before.day_tone == after.day_tone
        and before.group_tones == after.group_tones
        and before.audit.context_polarity_counts == after.audit.context_polarity_counts
        and before.audit.group_polarity_counts == after.audit.group_polarity_counts
        and before.audit.tone_scores == after.audit.tone_scores
        and before.audit.tone_trigger_keys == after.audit.tone_trigger_keys
        and before.audit.context_unit_ids == after.audit.context_unit_ids
    )


# END_BLOCK: TONE_REBIND


# START_BLOCK: ORCHESTRATION
def run_canonical_today_pipeline(
    raw_facts: Sequence[RawPhysicalFact],
    target_date: date,
    timezone_name: str,
    delta_trigger_semantic_keys: Sequence[str] | None = None,
    canon: TodayConvergenceCanon | None = None,
) -> CanonicalPipelineResult:
    # START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PIPELINE.run_canonical_today_pipeline
    # purpose: Compose canon, ledger, direct grouping, provisional tone, selection, and selected-only tone rebind.
    # inputs: raw_facts — normalized physical facts; target_date/timezone_name — presentation context; optional exact DayDelta keys and canon.
    # returns: CanonicalPipelineBuilt on success or CanonicalPipelineUnavailable at one typed stage boundary.
    # side_effects: reads frozen canon when omitted; no writes, network, database, or logs.
    # emitted_logs: none.
    # error_behavior: catches only typed canon/ledger/grouping/tone/selection errors at their declared stage; arbitrary exceptions propagate.
    # END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PIPELINE.run_canonical_today_pipeline
    try:
        resolved_canon = _resolve_canon(canon)
    except TodayConvergenceCanonError as exc:
        return _unavailable(canon=None, stage="canon", error=exc)

    try:
        ledger = build_canonical_ledger(
            raw_facts,
            resolved_canon,
            delta_trigger_semantic_keys,
        )
    except TodayConvergenceLedgerError as exc:
        return _unavailable(canon=resolved_canon, stage="ledger", error=exc)

    try:
        grouping = build_canonical_groups(ledger, resolved_canon)
    except TodayConvergenceGroupingError as exc:
        return _unavailable(canon=resolved_canon, stage="grouping", error=exc, ledger=ledger)

    try:
        provisional_tone = compute_canonical_tone(
            ledger,
            grouping,
            target_date,
            timezone_name,
            (),
            resolved_canon,
        )
    except TodayConvergenceToneError as exc:
        return _unavailable(
            canon=resolved_canon,
            stage="tone",
            error=exc,
            ledger=ledger,
            grouping=grouping,
        )

    try:
        selection = select_canonical_presentation(
            ledger,
            grouping,
            provisional_tone,
            target_date,
            timezone_name,
            resolved_canon,
        )
    except TodayConvergenceSelectionError as exc:
        return _unavailable(
            canon=resolved_canon,
            stage="selection",
            error=exc,
            ledger=ledger,
            grouping=grouping,
            tone=provisional_tone,
        )

    try:
        final_tone = compute_canonical_tone(
            ledger,
            grouping,
            target_date,
            timezone_name,
            selection.selected_unit_ids,
            resolved_canon,
        )
    except TodayConvergenceToneError:
        return _unavailable(
            canon=resolved_canon,
            stage="tone_rebind",
            error="today_convergence_pipeline:tone_selection_dependency",
            ledger=ledger,
            grouping=grouping,
            tone=provisional_tone,
        )

    if not _tone_facts_are_stable(provisional_tone, final_tone):
        return _unavailable(
            canon=resolved_canon,
            stage="tone_rebind",
            error="today_convergence_pipeline:tone_selection_dependency",
            ledger=ledger,
            grouping=grouping,
            tone=final_tone,
        )

    return CanonicalPipelineBuilt(
        formula_version=resolved_canon.formula_version,
        state=selection.state,
        ledger=ledger,
        grouping=grouping,
        tone=final_tone,
        selection=selection,
    )


# END_BLOCK: ORCHESTRATION


__all__ = [
    "CanonicalPipelineBuilt",
    "CanonicalPipelineResult",
    "CanonicalPipelineUnavailable",
    "run_canonical_today_pipeline",
]
