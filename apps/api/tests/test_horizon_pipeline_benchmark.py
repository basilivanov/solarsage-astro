# ############################################################################
# AI_HEADER: TEST_HORIZON_PIPELINE_BENCHMARK — B2B2 pipeline performance.
# ROLE: Measure p95 latency of full pipeline (selection → guidance → validator)
#       with a 120-activation layer producing 1728 combinations.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-HORIZON-PIPELINE-BENCHMARK
# purpose: Benchmark the full horizon pipeline asserting p95 < 100 ms with
#          120 activations (40/40/40) and 1728 combinations.
# owns:
#   - apps/api/tests/test_horizon_pipeline_benchmark.py
# inputs: Worst-case 120-activation synthetic layer.
# outputs: Measured p95 latency and standardized print line.
# dependencies: time stdlib, pytest, all pipeline services, testkit.
# side_effects: reads cached content canon.
# emitted_logs: none.
# invariants:
#   - 3 warmup runs before 20 measured runs.
#   - Every run includes full pipeline: selection, fact pack, tone, context,
#     guidance, validator.
#   - Excludes fixture construction, sidecar, DB, network, LLM, cold import.
# failure_policy: assertion failure when p95 >= 100 ms.
# END_MODULE_CONTRACT: M-TEST-HORIZON-PIPELINE-BENCHMARK

# START_MODULE_MAP: M-TEST-HORIZON-PIPELINE-BENCHMARK
# public_entrypoints:
#   - test_pipeline_benchmark
# semantic_blocks:
#   - BENCHMARK_MEASUREMENT
# owned_tests:
#   - apps/api/tests/test_horizon_pipeline_benchmark.py
# END_MODULE_MAP: M-TEST-HORIZON-PIPELINE-BENCHMARK

# START_BLOCK: BENCHMARK_MEASUREMENT
from __future__ import annotations

import math
import time

from app.schemas.horizon_guidance import HorizonGuidanceContext
from app.services.horizon_guidance_service import HorizonGuidanceService
from app.services.horizon_claim_validator import HorizonClaimValidator
from app.services.horizon_selection_service import HorizonSelectionService
from app.services.horizon_tone_service import HorizonToneService
from app.services.personal_fact_pack_service import PersonalFactPackService

from ._horizon_guidance_testkit import build_worst_case_pipeline_input


def test_pipeline_benchmark() -> None:
    """Measure full pipeline p95 with worst-case 120-activation input."""
    # START_FUNCTION_CONTRACT: F-TEST.test_pipeline_benchmark
    # purpose: test pipeline benchmark.
    # inputs: standard pytest fixtures.
    # returns: none.
    # side_effects: none.
    # emitted_logs: none.
    # error_behavior: test failure on assertion violation.
    # END_FUNCTION_CONTRACT: F-TEST.test_pipeline_benchmark
    layer, scoring, natal = build_worst_case_pipeline_input()

    # Verify exact shape of worst-case input before benchmarks
    assert len(layer.activations) == 120, f"expected 120 activations, got {len(layer.activations)}"
    assert sum(1 for a in layer.activations if a.id.startswith("long-bench-")) == 40
    assert sum(1 for a in layer.activations if a.id.startswith("medium-bench-")) == 40
    assert sum(1 for a in layer.activations if a.id.startswith("fast-bench-")) == 40

    guidance = HorizonGuidanceService()
    validator = HorizonClaimValidator()
    selection = HorizonSelectionService()

    runs_with_1728 = 0

    # Warmup: 3 runs — full pipeline
    for _ in range(3):
        result = selection.select(
            activation_layer=layer, scoring_result=scoring
        )
        assert result.selection is not None, "selection failed in warmup"
        assert result.diagnostics.per_horizon_post_bound_counts == {"long": 12, "medium": 12, "fast": 12}
        assert result.diagnostics.combinations_evaluated == 1728
        if result.diagnostics.combinations_evaluated == 1728:
            runs_with_1728 += 1

        fact_pack = PersonalFactPackService().build(
            selection=result.selection,
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal,
        )
        tone = HorizonToneService().assess(
            selection=result.selection,
            sphere_verdicts={},
        )
        ctx = HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=result.selection,
            fact_pack=fact_pack,
            tone_result=tone,
            sphere_verdicts={},
        )
        block = guidance.build(context=ctx)
        assert block.schema_version == "today-horizons.v1"
        assert block.guidance_mode == "deterministic"
        validator.validate(
            block=block,
            context=ctx,
            activation_evidence=list(layer.activations),
        )

    # Measured: 20 runs
    samples: list[float] = []
    for _ in range(20):
        start = time.perf_counter()

        # Full pipeline inside measurement
        result = selection.select(
            activation_layer=layer, scoring_result=scoring
        )
        assert result.selection is not None, "selection failed in measured"
        assert result.diagnostics.per_horizon_post_bound_counts == {"long": 12, "medium": 12, "fast": 12}
        assert result.diagnostics.combinations_evaluated == 1728
        if result.diagnostics.combinations_evaluated == 1728:
            runs_with_1728 += 1

        fact_pack = PersonalFactPackService().build(
            selection=result.selection,
            activation_layer=layer,
            scoring_result=scoring,
            natal_context=natal,
        )
        tone = HorizonToneService().assess(
            selection=result.selection,
            sphere_verdicts={},
        )
        ctx = HorizonGuidanceContext(
            schema_version="horizon-guidance-context.v1",
            selection=result.selection,
            fact_pack=fact_pack,
            tone_result=tone,
            sphere_verdicts={},
        )
        block = guidance.build(context=ctx)
        assert block.schema_version == "today-horizons.v1"
        assert block.guidance_mode == "deterministic"
        validator.validate(
            block=block,
            context=ctx,
            activation_evidence=list(layer.activations),
        )

        elapsed = (time.perf_counter() - start) * 1000
        samples.append(elapsed)

    samples.sort()
    n = len(samples)
    p95_index = math.ceil(0.95 * n) - 1
    p95_ms = round(samples[p95_index], 2)

    print(
        f"\nhorizon_pipeline_benchmark: p95={p95_ms}ms runs={n} combinations=1728 all_runs={runs_with_1728}/23"
    )

    assert p95_ms < 100, f"p95={p95_ms}ms >= 100ms"
    assert runs_with_1728 == 23, f"expected 23 runs with 1728 combinations, got {runs_with_1728}"


# END_BLOCK: BENCHMARK_MEASUREMENT
