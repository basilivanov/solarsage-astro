# ############################################################################
# AI_HEADER: MODULE_TEST_PAYLOAD_V2_DOWNSTREAM_MAPPING
# ROLE: W11 payload V2 evidence/score/why id preservation tests
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-PAYLOAD-V2-DOWNSTREAM-MAPPING
# purpose: Prove SemanticV2Service preserves activation ids and score/why references.
# owns:
#   - apps/api/tests/test_payload_v2_downstream_mapping.py
# inputs: fixtures/downstream_v2/*
# outputs: pytest assertions
# dependencies: ScoringV2Service, SemanticV2Service
# side_effects: none
# emitted_logs: none
# invariants: activationEvidence contains all sidecar ids; why/score ids are subset
# failure_policy: pytest fail
# END_MODULE_CONTRACT: M-TEST-PAYLOAD-V2-DOWNSTREAM-MAPPING

# START_MODULE_MAP: M-TEST-PAYLOAD-V2-DOWNSTREAM-MAPPING
# public_entrypoints: test_* functions
# END_MODULE_MAP: M-TEST-PAYLOAD-V2-DOWNSTREAM-MAPPING

from __future__ import annotations

import json
from pathlib import Path

from app.schemas.activation import ActivationLayer
from app.services.scoring_v2_service import ScoringV2Service
from app.services.semantic_v2_service import SemanticV2Service


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "downstream_v2"


def _layer(name: str) -> ActivationLayer:
    raw = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return ActivationLayer.model_validate(raw["activation_layer"])


def test_build_v2_block_preserves_all_sidecar_ids():
    layer = _layer("12_payload_mapping.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(activation_layer=layer, scoring_result=scoring, trace_id="t")
    assert {a.id for a in layer.activations} == {e.id for e in block.activation_evidence}


def test_score_breakdown_activation_ids_in_evidence():
    layer = _layer("01_planet_target_mapping.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(activation_layer=layer, scoring_result=scoring, trace_id="t")
    evidence_ids = {e.id for e in block.activation_evidence}
    for ss in (block.score_breakdown or {}).values():
        for c in ss.contributions:
            if c.source == "activation":
                assert c.source_id in evidence_ids
            elif c.source == "base_signal":
                assert str(c.source_id).startswith("base_signal:")
            elif c.source == "convergence":
                assert str(c.source_id).startswith("convergence:")
            elif c.source == "cap":
                assert str(c.source_id).startswith("cap:")


def test_why_today_ids_subset_of_evidence():
    layer = _layer("08_convergence_multi_family.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(activation_layer=layer, scoring_result=scoring, trace_id="t")
    evidence_ids = {e.id for e in block.activation_evidence}
    for item in block.why_today:
        for aid in item.activation_ids:
            assert aid in evidence_ids


def test_build_v2_block_requires_scoring_result_type():
    import inspect

    signature = inspect.signature(SemanticV2Service.build_v2_block)
    assert str(signature.parameters["scoring_result"].annotation) == "ScoringV2Result"


def test_canon_map_boundary_exact_nine_keys_from_scoring():
    """Prove scoring canon map cannot escape exact nine-key boundary."""
    from app.services.canon_service import get_canon_versions
    from app.schemas.scoring_v2 import ScoringV2Result
    import copy

    layer = _layer("12_payload_mapping.json")

    # Create scoring with poisoned canon_versions
    scoring = ScoringV2Result(
        scoring_version="ss-scoring-2.0",
        canon_versions={
            "spheres": "runtime-core-v9",  # known core key - should be accepted
            "dignities": "v1",  # known core key - should be accepted
            "horizon_selection": "stale-v0",  # horizon key - should be IGNORED
            "unknown_runtime_key": "sentinel",  # unknown key - should be IGNORED
        },
        day_status="steady",
        status_breakdown={},
        sphere_scores={},
        top_signals=[],
        top_activations=[],
        debug={},
    )

    # Capture original scoring map for byte-identity check
    scoring_copy = copy.deepcopy(scoring)

    # Build V2 block
    block = SemanticV2Service().build_v2_block(
        activation_layer=layer,
        scoring_result=scoring,
        trace_id="boundary-test",
    )

    # Get expected exact nine-key set from canonical source
    expected_nine = set(get_canon_versions().keys())
    actual_keys = set(block.audit.canon_versions.keys())

    # Prove exact canon versions key count
    assert actual_keys == expected_nine, f"Expected {expected_nine}, got {actual_keys}"
    assert len(block.audit.canon_versions) == len(get_canon_versions())

    # Prove known core keys preserved by merge semantics
    assert block.audit.canon_versions["spheres"] == "runtime-core-v9"
    assert block.audit.canon_versions["dignities"] == "v1"

    # Prove stale horizon_selection did NOT replace current horizon canon
    # (current value should come from horizon services, not scoring input)
    assert block.audit.canon_versions.get("horizon_selection") != "stale-v0"

    # Prove unknown runtime key absent
    assert "unknown_runtime_key" not in block.audit.canon_versions

    # Prove original scoring map byte-identical (not mutated)
    assert scoring_copy.canon_versions == scoring.canon_versions


def test_canon_map_boundary_incomplete_scoring_map():
    """Prove incomplete scoring map doesn't lose core keys."""
    from app.services.canon_service import get_canon_versions
    from app.schemas.scoring_v2 import ScoringV2Result

    layer = _layer("12_payload_mapping.json")

    # Create scoring with ONLY some core keys (incomplete map)
    scoring = ScoringV2Result(
        scoring_version="ss-scoring-2.0",
        canon_versions={
            "spheres": "v2-from-scoring",  # only one core key present
            # missing: dignities, aspect_rules, activation_rules, scoring_v2
        },
        day_status="steady",
        status_breakdown={},
        sphere_scores={},
        top_signals=[],
        top_activations=[],
        debug={},
    )

    # Build V2 block
    block = SemanticV2Service().build_v2_block(
        activation_layer=layer,
        scoring_result=scoring,
        trace_id="incomplete-test",
    )

    # Get expected exact nine-key set
    expected_nine = set(get_canon_versions().keys())
    actual_keys = set(block.audit.canon_versions.keys())

    # Prove exact nine-key set preserved
    assert actual_keys == expected_nine
    assert len(block.audit.canon_versions) == len(get_canon_versions())

    # Prove the one provided core key was merged
    assert block.audit.canon_versions["spheres"] == "v2-from-scoring"

    # Prove other core keys still present from base get_canon_versions()
    assert "dignities" in block.audit.canon_versions
    assert "aspect_rules" in block.audit.canon_versions
    assert "activation_rules" in block.audit.canon_versions
    assert "scoring_v2" in block.audit.canon_versions

    # Prove horizon keys present (from get_canon_versions())
    assert "horizon_selection" in block.audit.canon_versions
    assert "horizon_language_ru" in block.audit.canon_versions
    assert "horizon_actions_ru" in block.audit.canon_versions
    assert "personal_patterns_ru" in block.audit.canon_versions
