# ############################################################################
# AI_HEADER: MODULE_TEST_HOUSES
# ROLE: Unit tests for sidecar house lookup utility
# DEPENDENCIES: pytest, solarsage.utils.houses
# GRACE_ANCHORS: [HOUSE_FINDER_TESTS]
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HOUSES
# purpose: Verify find_house accuracy, cusp boundary matching, wrap-around, and invalid cusp handling.
# owns:
#   - apps/solarsage/tests/test_houses.py
# inputs: test cases
# outputs: assertions
# dependencies: solarsage.utils.houses
# side_effects: none
# emitted_logs: none
# failure_policy: fails test on miscalculated house
# END_MODULE_CONTRACT: M-TEST-HOUSES

# START_MODULE_MAP: M-TEST-HOUSES
# public_entrypoints:
#   - test_find_house_exact_cusp
#   - test_find_house_wrap_around
#   - test_find_house_invalid_cusps
# semantic_blocks:
#   - HOUSE_FINDER_TESTS: unit tests for find_house
# owned_tests:
#   - apps/solarsage/tests/test_houses.py
# END_MODULE_MAP: M-TEST-HOUSES

import pytest
from solarsage.utils.houses import find_house


# START_BLOCK: HOUSE_FINDER_TESTS
def test_find_house_standard_cusps():
    # 12 cusps spaced every 30 degrees starting at 0
    cusps = [float(i * 30) for i in range(12)]

    assert find_house(0.0, cusps) == 1
    assert find_house(15.0, cusps) == 1
    assert find_house(29.99, cusps) == 1
    assert find_house(30.0, cusps) == 2
    assert find_house(345.0, cusps) == 12
    assert find_house(359.99, cusps) == 12


def test_find_house_exact_cusp_boundary():
    """Planet exactly on cusp belongs to starting house [cusp, next)."""
    cusps = [15.0, 45.0, 75.0, 105.0, 135.0, 165.0, 195.0, 225.0, 255.0, 285.0, 315.0, 345.0]

    assert find_house(15.0, cusps) == 1
    assert find_house(45.0, cusps) == 2
    assert find_house(345.0, cusps) == 12


def test_find_house_wrap_around():
    """Cusp wrapping over 360/0 boundary (e.g. house 12 starts at 350° and ends at 20°)."""
    cusps = [20.0, 50.0, 80.0, 110.0, 140.0, 170.0, 200.0, 230.0, 260.0, 290.0, 320.0, 350.0]

    assert find_house(355.0, cusps) == 12
    assert find_house(5.0, cusps) == 12
    assert find_house(19.99, cusps) == 12
    assert find_house(20.0, cusps) == 1


def test_find_house_invalid_cusps():
    """Returns None when cusps are empty, None, or not 12 elements."""
    assert find_house(45.0, []) is None
    assert find_house(45.0, [0.0] * 5) is None
    assert find_house(45.0, [0.0] * 13) is None
# END_BLOCK: HOUSE_FINDER_TESTS
