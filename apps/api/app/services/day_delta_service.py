# ############################################################################
# AI_HEADER: MODULE_DAY_DELTA_SERVICE
# ROLE: Compare yesterday vs today signals, compute delta_kind and phase.
# DEPENDENCIES: app.schemas.normalization
# GRACE_ANCHORS: [COMPUTE_DELTAS]
# WAVE: W-PHASE-1
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-DELTA-SERVICE
# purpose: Compute deltas between yesterday's and today's signals.
# owns:
#   - apps/api/app/services/day_delta_service.py
# inputs:
#   - yesterday_signals: list[AstroSignal]
#   - today_signals: list[AstroSignal]
# outputs:
#   - list[AstroSignal] annotated with delta_kind and phase
# dependencies:
#   - M-CONTRACTS.normalization (AstroSignal)
# side_effects:
#   - none (pure computation)
# invariants:
#   - signals matched by stable key (type, planet, target_planet, house, sign)
#   - peak_today detected when strength >= yesterday's 0.95
# failure_policy:
#   - empty input returns empty output
# END_MODULE_CONTRACT: M-DAY-DELTA-SERVICE

# START_MODULE_MAP: M-DAY-DELTA-SERVICE
# public_entrypoints:
#   - DayDeltaService.compute_deltas
# semantic_blocks:
#   - COMPUTE_DELTAS: compute day-over-day signal deltas
# END_MODULE_MAP: M-DAY-DELTA-SERVICE

from app.schemas.normalization import AstroSignal


def _signal_key(s: AstroSignal) -> tuple:
    """Stable key for matching signals across days."""
    return (
        s.type,
        s.planet,
        s.target_planet,
        s.aspect_type,
        s.house,
        s.sign,
        s.technique,
    )


class DayDeltaService:
    """Compute delta between yesterday's and today's signals."""

    def __init__(
        self,
        yesterday_signals: list[AstroSignal],
        today_signals: list[AstroSignal],
    ):
        self.yesterday = {_signal_key(s): s for s in yesterday_signals}
        self.today = {_signal_key(s): s for s in today_signals}

    def compute_deltas(self) -> list[AstroSignal]:
        # START_FUNCTION_CONTRACT: F-M-DAY-DELTA-SERVICE.compute_deltas
        # purpose: Compare yesterday vs today signals, annotate with delta_kind and phase.
        # inputs: self with yesterday_signals and today_signals (from __init__)
        # returns: list[AstroSignal] with delta_kind, phase, daily_salience set
        # side_effects: none (pure computation)
        # emitted_logs: none
        # error_behavior: empty input returns empty list; never raises
        # END_FUNCTION_CONTRACT: F-M-DAY-DELTA-SERVICE.compute_deltas
        """Return today's signals annotated with delta_kind and phase."""
        result = []
        for s in list(self.today.values()):
            key = _signal_key(s)

            # Create copy to avoid mutating cached signals
            annotated = s.model_copy()

            was_yesterday = key in self.yesterday
            yesterday_signal = self.yesterday.get(key)

            if not was_yesterday:
                annotated.delta_kind = "new_today"
                annotated.phase = "entering"
                annotated.daily_salience = s.strength * 1.30
            elif yesterday_signal:
                str_diff = s.strength - yesterday_signal.strength
                threshold = 0.08

                if abs(str_diff) < threshold:
                    annotated.delta_kind = "background"
                    annotated.phase = "background"
                    annotated.daily_salience = s.strength * 0.55
                elif str_diff > threshold:
                    annotated.delta_kind = "stronger_than_yesterday"
                    annotated.phase = "applying"
                    annotated.daily_salience = s.strength * 1.15
                else:
                    annotated.delta_kind = "weaker_than_yesterday"
                    annotated.phase = "separating"
                    annotated.daily_salience = s.strength * 0.90

                # Peak detection
                if str_diff >= threshold and yesterday_signal.strength >= s.strength * 0.95:
                    annotated.delta_kind = "peak_today"
                    annotated.phase = "exact"
                    annotated.daily_salience = s.strength * 1.35
            else:
                annotated.delta_kind = "background"
                annotated.phase = "background"
                annotated.daily_salience = s.strength * 0.55

            result.append(annotated)

        return result
