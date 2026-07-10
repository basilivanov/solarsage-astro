"""W11 payload V2 downstream mapping invariants."""

from __future__ import annotations

import json
from pathlib import Path

from app.core.versions import SCORING_V2_VERSION
from app.schemas.activation import ActivationLayer
from app.schemas.scoring_v2 import ScoringV2Result, SphereContribution, SphereScoreV2
from app.services.scoring_v2_service import ScoringV2Service
from app.services.semantic_v2_service import SemanticV2Service


FIXTURE_DIR = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "downstream_v2"


def _layer(name: str) -> ActivationLayer:
    raw = json.loads((FIXTURE_DIR / name).read_text(encoding="utf-8"))
    return ActivationLayer.model_validate(raw["activation_layer"])


def test_build_v2_block_preserves_activation_ids():
    layer = _layer("12_payload_mapping.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(
        activation_layer=layer,
        scoring_result=scoring,
        v1_v2_diff=None,
        trace_id="t",
    )
    payload_ids = {e.id for e in block.activation_evidence}
    sidecar_ids = {a.id for a in layer.activations}
    assert sidecar_ids <= payload_ids
    assert sidecar_ids == payload_ids


def test_score_breakdown_contribution_ids_traceable():
    layer = _layer("01_planet_target_mapping.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(
        activation_layer=layer,
        scoring_result=scoring,
        v1_v2_diff=None,
        trace_id="t",
    )
    evidence_ids = {e.id for e in block.activation_evidence}
    for skey, ss in (block.score_breakdown or {}).items():
        for c in ss.contributions:
            if c.source == "activation":
                assert c.source_id in evidence_ids


def test_why_today_activation_ids_subset_of_evidence():
    layer = _layer("08_convergence_multi_family.json")
    scoring = ScoringV2Service().score_day([], layer)
    block = SemanticV2Service().build_v2_block(
        activation_layer=layer,
        scoring_result=scoring,
        v1_v2_diff=None,
        trace_id="t",
    )
    evidence_ids = {e.id for e in block.activation_evidence}
    for item in block.why_today:
        for aid in item.activation_ids:
            assert aid in evidence_ids


def test_build_v2_block_requires_scoring_result():
    layer = _layer("12_payload_mapping.json")
    try:
        SemanticV2Service().build_v2_block(
            activation_layer=layer,
            scoring_result=None,
        )
        assert False, "expected ValueError"
    except ValueError as e:
        assert "scoring_result is required" in str(e)
