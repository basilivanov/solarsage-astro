# ############################################################################
# AI_HEADER: MODULE_DAY_SCORING_SIGNALS — shared day-scoring signal filter.
# ROLE: Shared helper used by /day and calendar status calculation so both paths
#       score the same dynamic transit/day signals and ignore static natal base.
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-SCORING-SIGNALS
# purpose: Filter normalized AstroSignal rows down to signals that are allowed to
#          affect daily verdict/status scoring.
# owns:
#   - apps/api/app/services/day_scoring_signals.py
# inputs: list[AstroSignal] from NormalizationService.normalize_day().
# outputs: list[AstroSignal] containing transit/current day signals only.
# dependencies: app.schemas.normalization.AstroSignal.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Static natal planet/sign/house/aspect signals never dominate day scoring.
#   - Transit-prefixed aspects and planet-in-house signals are preserved.
# failure_policy: Pure filter; malformed missing planet names are treated as non-day signals.
# END_MODULE_CONTRACT: M-DAY-SCORING-SIGNALS

# START_MODULE_MAP: M-DAY-SCORING-SIGNALS
# public_entrypoints:
#   - is_day_scored_signal
#   - filter_day_scored_signals
# semantic_blocks:
#   - DAY_SIGNAL_FILTER: shared predicate and list filter
# owned_tests:
#   - apps/api/tests/test_calendar_endpoints.py
#   - apps/api/tests/test_day_endpoints.py
# END_MODULE_MAP: M-DAY-SCORING-SIGNALS

from __future__ import annotations

from app.schemas.normalization import AstroSignal


DAY_EVENT_SIGNAL_TYPES = frozenset({"lunar", "void_moon", "retrograde", "day_event"})


# START_BLOCK: DAY_SIGNAL_FILTER
def is_day_scored_signal(signal: AstroSignal) -> bool:
    # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-SIGNALS.is_day_scored_signal
    # purpose: Decide whether one AstroSignal is eligible for day scoring.
    # inputs: signal — normalized astrological signal.
    # returns: bool — true for transit-prefixed or explicit day-event signals.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Missing planet/type values return false unless type is a known day event.
    # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-SIGNALS.is_day_scored_signal
    return (signal.planet or "").startswith("Transit_") or signal.type in DAY_EVENT_SIGNAL_TYPES


def filter_day_scored_signals(signals: list[AstroSignal]) -> list[AstroSignal]:
    # START_FUNCTION_CONTRACT: F-M-DAY-SCORING-SIGNALS.filter_day_scored_signals
    # purpose: Return the canonical day-scored subset shared by TodayService and CalendarService.
    # inputs: signals — combined natal + transit normalized signals.
    # returns: list[AstroSignal] — stable-order filtered day-scored signals.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: Pure list comprehension; input validation remains owned by Pydantic.
    # END_FUNCTION_CONTRACT: F-M-DAY-SCORING-SIGNALS.filter_day_scored_signals
    return [signal for signal in signals if is_day_scored_signal(signal)]
# END_BLOCK: DAY_SIGNAL_FILTER
