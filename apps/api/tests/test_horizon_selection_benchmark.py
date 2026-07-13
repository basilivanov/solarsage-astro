# ############################################################################
# AI_HEADER: TEST_HORIZON_SELECTION_BENCHMARK — B2A bounded selector micro-benchmark.
# ROLE: Measures deterministic selection service latency on a synthetic 120-activation input.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-BENCHMARK
# purpose: Enforce the B2A selector latency and bounded-combination budget without external I/O.
# owns:
#   - apps/api/tests/test_horizon_selection_benchmark.py
# inputs: Synthetic 120-activation layer and scoring payload.
# outputs: Printed p95 evidence plus deterministic performance assertions.
# dependencies: math/time stdlib, B2A schemas and selection service.
# side_effects: stdout benchmark line only.
# emitted_logs: none.
# invariants:
#   - exactly 20 measured runs follow 3 warmups.
#   - p95 is under 100ms and cartesian combinations never exceed 1728.
# failure_policy: assertion failure on performance or bound regression.
# END_MODULE_CONTRACT: M-TEST-HORIZON-SELECTION-BENCHMARK

# START_MODULE_MAP: M-TEST-HORIZON-SELECTION-BENCHMARK
# public_entrypoints:
#   - test_horizon_selection_benchmark
# semantic_blocks:
#   - HORIZON_SELECTION_BENCHMARK_FIXTURES: synthetic activation factory.
#   - HORIZON_SELECTION_BENCHMARK_TEST: warmup and measured execution loop.
# owned_tests:
#   - apps/api/tests/test_horizon_selection_benchmark.py
# END_MODULE_MAP: M-TEST-HORIZON-SELECTION-BENCHMARK

# START_BLOCK: HORIZON_SELECTION_BENCHMARK_FIXTURES
from __future__ import annotations

import math
import time

from app.schemas.activation import ActivationEvidence, ActivationLayer
from app.schemas.scoring_v2 import ScoringV2Result, SphereContribution, SphereScoreV2
from app.services.horizon_selection_service import HorizonSelectionService
# END_BLOCK: HORIZON_SELECTION_BENCHMARK_FIXTURES


def _activation(index: int) -> ActivationEvidence:
    horizon_mod = index % 3
    if horizon_mod == 0:
        return ActivationEvidence(id=f"long-{index:03d}", technique="annual_profection", technique_family="profection", target_type="planet", target_key="SATURN", kind="story", strength=0.75, evidence="bench", active_from="2026-01-01", active_until="2026-12-31", target_planet="SATURN")
    if horizon_mod == 1:
        return ActivationEvidence(id=f"medium-{index:03d}", technique="transit_to_natal", technique_family="transit", target_type="planet", target_key="SATURN", kind="story", strength=0.72, evidence="bench", source_planet="PLUTO", target_planet="SATURN", active_from="2026-03-01T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-09-30T00:00:00Z")
    return ActivationEvidence(id=f"fast-{index:03d}", technique="transit_to_natal", technique_family="transit", target_type="planet", target_key="PLUTO", kind="story", strength=0.70, evidence="bench", source_planet="MOON", target_planet="PLUTO", active_from="2026-07-12T00:00:00Z", exact_at="2026-07-12T12:00:00Z", active_until="2026-07-12T23:00:00Z")


# START_BLOCK: HORIZON_SELECTION_BENCHMARK_TEST
def test_horizon_selection_benchmark() -> None:
    # START_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-BENCHMARK.test_horizon_selection_benchmark
    # purpose: Measure 20 bounded selection runs after warmup and enforce B2A latency budget.
    # inputs: none.
    # returns: none.
    # side_effects: stdout benchmark evidence only.
    # emitted_logs: none.
    # error_behavior: assertion failure when p95 or combination limits regress.
    # END_FUNCTION_CONTRACT: F-M-TEST-HORIZON-SELECTION-BENCHMARK.test_horizon_selection_benchmark
    activations = [_activation(index) for index in range(120)]
    layer = ActivationLayer(calculation_version="calc", target_date="2026-07-12", target_time="12:00", target_tz="UTC", house_system="WHOLE_SIGN", activations=activations, by_planet={}, by_house={}, by_lot={}, by_angle={})
    sphere_scores = {
        "work_status_achievement": SphereScoreV2(key="work_status_achievement", title="work", base_score=0.0, activation_score=40.0, convergence_bonus=0.0, raw_score=40.0, final_score=40.0, contributions=[SphereContribution(sphere="work_status_achievement", source="activation", source_id=activation.id, amount=1.0, evidence="bench") for activation in activations if activation.id.startswith("long-")]),
        "crisis_transformation_control": SphereScoreV2(key="crisis_transformation_control", title="crisis", base_score=0.0, activation_score=80.0, convergence_bonus=0.0, raw_score=80.0, final_score=80.0, contributions=[SphereContribution(sphere="crisis_transformation_control", source="activation", source_id=activation.id, amount=1.0, evidence="bench") for activation in activations if activation.id.startswith(("medium-", "fast-"))]),
    }
    scoring = ScoringV2Result(canon_versions={"spheres": "v1"}, day_status="supportive", status_breakdown={}, sphere_scores=sphere_scores, top_signals=[], top_activations=activations)
    service = HorizonSelectionService()

    for _ in range(3):
        service.select(activation_layer=layer, scoring_result=scoring)

    samples_ns: list[int] = []
    last_result = None
    for _ in range(20):
        start = time.perf_counter_ns()
        last_result = service.select(activation_layer=layer, scoring_result=scoring)
        samples_ns.append(time.perf_counter_ns() - start)

    samples_ns.sort()
    p95_index = math.ceil(0.95 * len(samples_ns)) - 1
    p95_ms = samples_ns[p95_index] / 1_000_000
    assert last_result is not None
    assert last_result.diagnostics.combinations_evaluated == 1728
    print(f"benchmark: p95={p95_ms:.3f}ms runs=20 combinations={last_result.diagnostics.combinations_evaluated}")
    assert p95_ms < 100
# END_BLOCK: HORIZON_SELECTION_BENCHMARK_TEST
