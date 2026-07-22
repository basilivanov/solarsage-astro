# ############################################################################
# AI_HEADER: MODULE_TESTS_TODAY_TEST_FIXTURES — shared Today test fixtures.
# ROLE: Small shared deterministic fixtures for TodayService tests (not a
#       harness): a contract-valid interpretation tuple that is cacheable and
#       CPU-cheap, so cache-identity tests never depend on wall-clock.
# ############################################################################

# START_MODULE_CONTRACT: M-TESTS-TODAY-TEST-FIXTURES
# purpose: Provide a deterministic, contract-valid interpretation result
#   (ConcreteAdviceBlock with 12 non-fallback rows, valid DaySummaryBlock,
#   allowed DayChart | None) for tests whose subject is scoring/cache
#   identity — never the interpretation internals.
# owns:
#   - apps/api/tests/today_test_fixtures.py
# inputs: none.
# outputs: build_deterministic_interpretation_result() -> tuple.
# dependencies: app.schemas.today, today_interpretation_service constants.
# side_effects: none.
# emitted_logs: none.
# invariants:
#   - Every row carries real text (never the fallback constant), so the
#     payload is cacheable (>= 9 non-fallback rows).
# failure_policy: n/a (pure constructors).
# END_MODULE_CONTRACT: M-TESTS-TODAY-TEST-FIXTURES

# START_MODULE_MAP: M-TESTS-TODAY-TEST-FIXTURES
# public_entrypoints:
#   - build_deterministic_interpretation_result
# semantic_blocks:
#   - INTERPRETATION_FIXTURE: deterministic contract-valid interpretation tuple
# owned_tests:
#   - apps/api/tests/test_today_cache_v2_key.py
#   - apps/api/tests/test_today_meta_versions.py
# END_MODULE_MAP: M-TESTS-TODAY-TEST-FIXTURES

from __future__ import annotations

from app.schemas.today import (
    ConcreteAdviceBlock,
    ConcreteAdviceCounts,
    ConcreteAdviceEvidence,
    ConcreteAdviceRow,
    DayChart,
    DaySummaryBlock,
)
from app.services.today_interpretation_service import CANONICAL_PRODUCT_SPHERES


# START_BLOCK: INTERPRETATION_FIXTURE
def build_deterministic_interpretation_result() -> (
    tuple[ConcreteAdviceBlock, DaySummaryBlock, DayChart | None]
):
    # START_FUNCTION_CONTRACT: F-M-TESTS-TODAY-TEST-FIXTURES.build_deterministic_interpretation_result
    # purpose: Build a contract-valid deterministic interpretation tuple for
    #   cache-identity tests whose subject is NOT the interpretation internals.
    # inputs: none.
    # returns: (ConcreteAdviceBlock with 12 non-fallback rows, valid
    #   DaySummaryBlock, DayChart | None).
    # side_effects: none (pure constructors).
    # emitted_logs: none.
    # error_behavior: n/a (pure function; schema validation errors would
    #   propagate from the contract models).
    # END_FUNCTION_CONTRACT: F-M-TESTS-TODAY-TEST-FIXTURES.build_deterministic_interpretation_result
    rows = [
        ConcreteAdviceRow(
            key=canon["key"],
            label=canon["label"],
            icon_name=canon["icon_name"],
            rank=index,
            verdict="neutral",
            confidence="low",
            text=f"Спокойный день для дела номер {index}.",
            evidence=[
                ConcreteAdviceEvidence(
                    kind="day_status",
                    title="Общий статус дня: steady",
                )
            ],
        )
        for index, canon in enumerate(CANONICAL_PRODUCT_SPHERES, 1)
    ]
    concrete_advice = ConcreteAdviceBlock(
        rows=rows,
        counts=ConcreteAdviceCounts(good=0, caution=0, avoid=0, neutral=12),
    )
    day_summary = DaySummaryBlock(
        status_label="Ровный",
        status_line="Спокойный день",
        facts=[],
    )
    return concrete_advice, day_summary, None
# END_BLOCK: INTERPRETATION_FIXTURE
