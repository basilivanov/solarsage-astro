# ############################################################################
# AI_HEADER: MODULE_DAY_RELATIVE_STATUS
# ROLE: Pure service module calculating user-relative day status against 14-day baseline.
# DEPENDENCIES: math, typing, app.schemas.day
# GRACE_ANCHORS: [RELATIVE_STATUS_CALCULATOR]
# ############################################################################

# START_MODULE_CONTRACT: M-DAY-RELATIVE-STATUS
# purpose: Compute relative day status (z-score against 14-day personal baseline, hysteresis, absolute overrides, cold start fallback).
# owns:
#   - apps/api/app/services/day_relative_status.py
# inputs:
#   - today_support: float
#   - today_tension: float
#   - absolute_v2_status: str
#   - history: list[dict[str, float]]
# outputs:
#   - RelativeDayStatusRead
# invariants:
#   - History < 5 days -> mode="absolute", fallback status mapped from v2_status
#   - History >= 5 days -> mode="relative", z-scores computed with std floor 0.5
#   - Absolute extremes (hard/strong) override relative status
#   - Hysteresis requires z >= 0.75 two days in a row (today + yesterday in history)
#   - Fully deterministic math, zero external or LLM calls
# END_MODULE_CONTRACT: M-DAY-RELATIVE-STATUS

# START_MODULE_MAP: M-DAY-RELATIVE-STATUS
# public_entrypoints:
#   - compute_relative_status
# semantic_blocks:
#   - RELATIVE_STATUS_CALCULATOR: compute_relative_status implementation
# owned_tests:
#   - apps/api/tests/test_day_relative_status.py
# END_MODULE_MAP: M-DAY-RELATIVE-STATUS

from __future__ import annotations

import math
from typing import Literal

from app.schemas.day import RelativeDayStatusRead, RelativeStatusBaseline

STATUS_LABELS: dict[str, str] = {
    "usual": "Обычный день",
    "softer": "Легче, чем обычно",
    "tenser": "Напряжённее обычного",
    "hard": "Тяжёлый день",
    "strong": "Сильный день",
}


# START_BLOCK: RELATIVE_STATUS_CALCULATOR
def compute_relative_status(
    today_support: float,
    today_tension: float,
    absolute_v2_status: str,
    history: list[dict[str, float]],
) -> RelativeDayStatusRead:
    # START_FUNCTION_CONTRACT: F-M-DAY-RELATIVE-STATUS.compute_relative_status
    # purpose: Calculate user-relative day status with z-scores, hysteresis, and absolute boundary overrides.
    # inputs: today_support (float), today_tension (float), absolute_v2_status (str), history (list[dict])
    # returns: RelativeDayStatusRead
    # side_effects: none (pure calculation)
    # emitted_logs: none
    # error_behavior: handles empty/short history gracefully with absolute mode fallback
    # END_FUNCTION_CONTRACT: F-M-DAY-RELATIVE-STATUS.compute_relative_status
    n = len(history)

    # 1. Cold start fallback (< 5 historical days)
    if n < 5:
        mode: Literal["absolute", "relative"] = "absolute"
        status_code: Literal["usual", "softer", "tenser", "hard", "strong"] = (
            "hard"
            if absolute_v2_status == "tense"
            else "strong"
            if absolute_v2_status == "supportive"
            else "usual"
        )
        label = STATUS_LABELS[status_code]

        supp_marker = min(1.0, max(0.0, today_support / 100.0))
        tens_marker = min(1.0, max(0.0, today_tension / 100.0))

        return RelativeDayStatusRead(
            mode=mode,
            status=status_code,
            label=label,
            z_support=0.0,
            z_tension=0.0,
            support_band=[0.0, 100.0],
            tension_band=[0.0, 100.0],
            support_marker=supp_marker,
            tension_marker=tens_marker,
            baseline=RelativeStatusBaseline(
                support_mean=0.0,
                support_std=0.5,
                tension_mean=0.0,
                tension_std=0.5,
                days=n,
            ),
        )

    # 2. History >= 5 days -> Relative Mode
    mode = "relative"
    supp_mean = sum(h["support"] for h in history) / n
    tens_mean = sum(h["tension"] for h in history) / n

    supp_variance = sum((h["support"] - supp_mean) ** 2 for h in history) / n
    tens_variance = sum((h["tension"] - tens_mean) ** 2 for h in history) / n

    supp_std = max(0.5, math.sqrt(supp_variance))
    tens_std = max(0.5, math.sqrt(tens_variance))

    z_support = (today_support - supp_mean) / supp_std
    z_tension = (today_tension - tens_mean) / tens_std

    # Yesterday z-scores for hysteresis check
    yesterday_supp = history[0]["support"]
    yesterday_tens = history[0]["tension"]
    z_yesterday_supp = (yesterday_supp - supp_mean) / supp_std
    z_yesterday_tens = (yesterday_tens - tens_mean) / tens_std

    # Relative status decision with 2-day hysteresis
    if z_tension >= 0.75 and z_yesterday_tens >= 0.75:
        status_code = "tenser"
    elif z_support >= 0.75 and z_yesterday_supp >= 0.75:
        status_code = "softer"
    else:
        status_code = "usual"

    # Absolute boundary override (extremes win over relative status)
    if absolute_v2_status == "tense":
        status_code = "hard"
    elif absolute_v2_status == "supportive":
        status_code = "strong"

    label = STATUS_LABELS[status_code]

    supp_band = [max(0.0, supp_mean - supp_std), max(0.0, supp_mean + supp_std)]
    tens_band = [max(0.0, tens_mean - tens_std), max(0.0, tens_mean + tens_std)]

    supp_max = max(1.0, (supp_mean + supp_std) * 1.5)
    tens_max = max(1.0, (tens_mean + tens_std) * 1.5)

    supp_marker = min(1.0, max(0.0, today_support / supp_max))
    tens_marker = min(1.0, max(0.0, today_tension / tens_max))

    return RelativeDayStatusRead(
        mode=mode,
        status=status_code,
        label=label,
        z_support=round(z_support, 2),
        z_tension=round(z_tension, 2),
        support_band=[round(supp_band[0], 2), round(supp_band[1], 2)],
        tension_band=[round(tens_band[0], 2), round(tens_band[1], 2)],
        support_marker=round(supp_marker, 2),
        tension_marker=round(tens_marker, 2),
        baseline=RelativeStatusBaseline(
            support_mean=round(supp_mean, 2),
            support_std=round(supp_std, 2),
            tension_mean=round(tens_mean, 2),
            tension_std=round(tens_std, 2),
            days=n,
        ),
    )
# END_BLOCK: RELATIVE_STATUS_CALCULATOR
