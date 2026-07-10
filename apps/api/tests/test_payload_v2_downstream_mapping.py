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


def test_build_v2_block_requires_scoring_result():
    layer = _layer("12_payload_mapping.json")
    try:
        SemanticV2Service().build_v2_block(activation_layer=layer, scoring_result=None)
        assert False, "expected ValueError"
    except ValueError as e:
        assert "scoring_result is required" in str(e)
