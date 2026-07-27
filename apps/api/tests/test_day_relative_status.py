# ############################################################################
# AI_HEADER: MODULE_TEST_DAY_RELATIVE_STATUS
# ROLE: Unit tests for user-relative day status calculation module
# DEPENDENCIES: pytest, app.services.day_relative_status
# GRACE_ANCHORS: [RELATIVE_STATUS_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DAY-RELATIVE-STATUS
# purpose: Verify cold-start fallback, z-score computation, std floor, hysteresis, and absolute overrides.
# owns:
#   - apps/api/tests/test_day_relative_status.py
# inputs: test cases
# outputs: assertions
# dependencies: app.services.day_relative_status
# side_effects: none
# emitted_logs: none
# failure_policy: fails test on miscalculated relative status
# END_MODULE_CONTRACT: M-TEST-DAY-RELATIVE-STATUS

# START_MODULE_MAP: M-TEST-DAY-RELATIVE-STATUS
# public_entrypoints:
#   - test_cold_start_fallback
#   - test_relative_mode_z_scores
#   - test_std_floor
#   - test_hysteresis_two_day_requirement
#   - test_absolute_override_tense_and_supportive
# semantic_blocks:
#   - RELATIVE_STATUS_TESTS: unit tests for day_relative_status
# owned_tests:
#   - apps/api/tests/test_day_relative_status.py
# END_MODULE_MAP: M-TEST-DAY-RELATIVE-STATUS

import pytest
from app.services.day_relative_status import compute_relative_status


# START_BLOCK: RELATIVE_STATUS_TESTS
def test_cold_start_fallback():
    """Fewer than 5 historical days returns mode=absolute and fallback status."""
    history = [{"support": 50.0, "tension": 20.0}] * 4

    res = compute_relative_status(60.0, 30.0, "steady", history)
    assert res.mode == "absolute"
    assert res.status == "usual"
    assert res.label == "Обычный день"
    assert res.baseline.days == 4

    res_hard = compute_relative_status(60.0, 30.0, "tense", history)
    assert res_hard.status == "hard"
    assert res_hard.label == "Тяжёлый день"

    res_strong = compute_relative_status(60.0, 30.0, "supportive", history)
    assert res_strong.status == "strong"
    assert res_strong.label == "Сильный день"


def test_std_floor():
    """When history is constant, std uses the floor of 0.5 without division by zero."""
    history = [{"support": 50.0, "tension": 20.0}] * 7

    res = compute_relative_status(50.0, 20.0, "steady", history)
    assert res.mode == "relative"
    assert res.baseline.support_std == 0.5
    assert res.baseline.tension_std == 0.5
    assert res.z_support == 0.0
    assert res.z_tension == 0.0


def test_hysteresis_two_day_requirement():
    """z >= 0.75 requires two days in a row (today + yesterday in history[0]) to trigger tenser or softer."""
    # History of 7 days with support mean = 50, std ~ 5
    base_history = [
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
        {"support": 50.0, "tension": 20.0},
    ]

    # Case A: Only TODAY is high tension (yesterday was normal 20.0) -> stays "usual" due to hysteresis!
    res_one_day = compute_relative_status(50.0, 80.0, "steady", base_history)
    assert res_one_day.status == "usual"

    # Case B: Yesterday WAS high tension (history[0].tension = 80.0) AND today tension = 80.0 -> triggers "tenser"!
    two_day_tension_history = [{"support": 50.0, "tension": 80.0}] + base_history[1:]
    res_two_day = compute_relative_status(50.0, 80.0, "steady", two_day_tension_history)
    assert res_two_day.status == "tenser"
    assert res_two_day.label == "Напряжённее обычного"

    # Case C: Two days in a row high support -> triggers "softer"!
    two_day_support_history = [{"support": 80.0, "tension": 20.0}] + base_history[1:]
    res_softer = compute_relative_status(80.0, 20.0, "steady", two_day_support_history)
    assert res_softer.status == "softer"
    assert res_softer.label == "Легче, чем обычно"


def test_absolute_override_tense_and_supportive():
    """Absolute extremes (tense/supportive) override relative status regardless of z-score."""
    base_history = [{"support": 50.0, "tension": 20.0}] * 7

    # Absolute tense -> hard
    res_hard = compute_relative_status(50.0, 20.0, "tense", base_history)
    assert res_hard.status == "hard"
    assert res_hard.label == "Тяжёлый день"

    # Absolute supportive -> strong
    res_strong = compute_relative_status(50.0, 20.0, "supportive", base_history)
    assert res_strong.status == "strong"
    assert res_strong.label == "Сильный день"


def test_zone_markers_clipped():
    """Zone markers are clipped in range 0.0 .. 1.0."""
    history = [{"support": 50.0, "tension": 20.0}] * 7

    res_zero = compute_relative_status(0.0, 0.0, "steady", history)
    assert res_zero.support_marker == 0.0
    assert res_zero.tension_marker == 0.0

    res_high = compute_relative_status(200.0, 200.0, "steady", history)
    assert res_high.support_marker == 1.0
    assert res_high.tension_marker == 1.0
# END_BLOCK: RELATIVE_STATUS_TESTS
