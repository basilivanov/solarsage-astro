# ############################################################################
# AI_HEADER: TEST_DIRECT_REPLAY_PIPELINE — direct factor/replay regression tests.
# ROLE: Proves the HTTP-free path builds product factors and preserves C1 output
#       when low-significance timing is deferred.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-DIRECT-REPLAY-PIPELINE
# purpose: Validate direct ephemeris-to-factor calculation on the owner fixture.
# owns:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_direct_replay_pipeline.py
# inputs: deterministic Basil chart and 2026-07-08 target date.
# outputs: pytest assertions for ledger integrity and C1 equivalence.
# dependencies: direct_replay_pipeline; ablation_harness.
# side_effects: none.
# emitted_logs: none.
# invariants: scoped timing changes latency/audit only, not C1 state or hero IDs.
# failure_policy: tests fail on any drift.
# END_MODULE_CONTRACT: M-TEST-DIRECT-REPLAY-PIPELINE

# START_MODULE_MAP: M-TEST-DIRECT-REPLAY-PIPELINE
# public_entrypoints: none
# semantic_blocks:
#   - DIRECT_DAY: factor construction smoke.
#   - TIMING_EQUIVALENCE: full/scoped C1 parity.
# owned_tests:
#   - docs/work/2026-07-29_today-convergence-rewrite/analysis/test_direct_replay_pipeline.py
# END_MODULE_MAP: M-TEST-DIRECT-REPLAY-PIPELINE

from __future__ import annotations

from datetime import date as Date, timedelta

from ablation_harness import classify_day_v2
from direct_replay_pipeline import ChartInput, DirectReplayPipeline


BASIL = ChartInput(
    chart_id="owner-basil",
    birth_date="1980-10-30",
    birth_time="19:50",
    birth_lat=67.9394,
    birth_lon=32.8144,
    birth_tz="Europe/Moscow",
    target_tz="Europe/Moscow",
    current_lat=55.7558,
    current_lon=37.6173,
    current_tz="Europe/Moscow",
)
TARGET = Date(2026, 7, 8)


def _calculate(pipeline: DirectReplayPipeline):
    prepared = pipeline.prepare_chart(BASIL)
    previous_target = pipeline.prepare_target(
        target_date=(TARGET - timedelta(days=1)).isoformat(),
        target_tz=BASIL.target_tz,
    )
    previous_signals = pipeline.normalize_signals(prepared, previous_target)
    target = pipeline.prepare_target(
        target_date=TARGET.isoformat(),
        target_tz=BASIL.target_tz,
    )
    return pipeline.calculate_factor_day(
        prepared=prepared,
        target=target,
        previous_signals=previous_signals,
    )


# START_BLOCK: DIRECT_DAY
def test_direct_day_builds_canonical_factor_ledger() -> None:
    day = _calculate(DirectReplayPipeline(timing_scope="convergence_eligible"))
    semantic_keys = {factor["semantic_key"] for factor in day.factors}

    assert day.target_date == TARGET.isoformat()
    assert day.raw_activation_count > 100
    assert day.raw_ledger_count > 100
    assert day.invalid_ledger_count == 0
    assert day.timing_deferred_count > 0
    assert "aspect:PLUTO:trine:natal_planet:SATURN" in semantic_keys
    unresolved = [factor for factor in day.factors if not factor["spheres"]]
    assert unresolved
    assert all(factor["facet"] is None for factor in unresolved)
# END_BLOCK: DIRECT_DAY


# START_BLOCK: TIMING_EQUIVALENCE
def test_scoped_timing_preserves_c1_classification() -> None:
    full = _calculate(DirectReplayPipeline(timing_scope="all"))
    scoped = _calculate(DirectReplayPipeline(timing_scope="convergence_eligible"))
    full_result = classify_day_v2(
        list(full.factors),
        0.55,
        0.5,
        trigger_keys=set(full.trigger_keys),
    )
    scoped_result = classify_day_v2(
        list(scoped.factors),
        0.55,
        0.5,
        trigger_keys=set(scoped.trigger_keys),
    )

    assert {factor["factor_id"] for factor in scoped.factors} == {
        factor["factor_id"] for factor in full.factors
    }
    assert scoped_result["state"] == full_result["state"]
    assert {
        group["hero_anchor"]["semantic_key"]
        for group in scoped_result["hero_groups"]
    } == {
        group["hero_anchor"]["semantic_key"]
        for group in full_result["hero_groups"]
    }
    assert scoped.timing_deferred_count > 0
    assert full.timing_deferred_count == 0
# END_BLOCK: TIMING_EQUIVALENCE
