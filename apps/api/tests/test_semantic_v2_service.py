import pytest
from datetime import date as Date
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.schemas.scoring_v2 import ScoringV2Result, SphereScoreV2, SphereContribution
from app.services.semantic_v2_service import SemanticV2Service

@pytest.fixture
def empty_activation_layer():
    return ActivationLayer(
        calculation_version="ss-calc-1.1.0",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )

def test_semantic_v2_service_no_convergence(empty_activation_layer):
    service = SemanticV2Service()
    # Add a single activation
    empty_activation_layer.activations.append(
        ActivationEvidence(
            id="act1",
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="MERCURY",
            kind="aspect",
            strength=0.8,
            evidence="Transit Moon opposition natal Mercury",
        )
    )
    block = service.build_v2_block(activation_layer=empty_activation_layer)
    assert block.activation_summary.headline == "День в основном определяется текущими транзитами, без сильной сходимости долгих техник."
    assert len(block.why_today) == 1
    assert block.why_today[0].id == "fallback-no-convergence"

def test_semantic_v2_service_with_convergence(empty_activation_layer):
    service = SemanticV2Service()
    # Add multiple activations from different families targeting MERCURY
    empty_activation_layer.activations.extend([
        ActivationEvidence(
            id="act1",
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="MERCURY",
            kind="aspect",
            strength=0.8,
            evidence="Transit Moon opposition natal Mercury",
        ),
        ActivationEvidence(
            id="act2",
            technique="annual_profection",
            technique_family="profection",
            target_type="planet",
            target_key="MERCURY",
            kind="lord_of_year",
            strength=0.75,
            evidence="Mercury is lord of year",
        )
    ])
    block = service.build_v2_block(activation_layer=empty_activation_layer)
    assert "сходятся 2 независимые техники" in block.activation_summary.headline
    assert len(block.why_today) == 2
    assert {item.id for item in block.why_today} == {"why-planet-MERCURY-transit", "why-planet-MERCURY-profection"}

def test_semantic_v2_service_get_evidence_for_sphere(empty_activation_layer):
    service = SemanticV2Service()
    # Add activation targeting MERCURY (which maps to thinking_speech_learning)
    empty_activation_layer.activations.append(
        ActivationEvidence(
            id="act1",
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="MERCURY",
            kind="aspect",
            strength=0.8,
            evidence="Transit Moon opposition natal Mercury",
        )
    )

    # Mock scoring result with contribution for thinking_speech_learning
    scoring_result = ScoringV2Result(
        scoring_version="ss-scoring-2.0",
        canon_versions={"spheres": "v1"},
        day_status="steady",
        status_breakdown={},
        sphere_scores={
            "thinking_speech_learning": SphereScoreV2(
                key="thinking_speech_learning",
                title="мысли",
                base_score=1.0,
                activation_score=0.5,
                convergence_bonus=0.0,
                raw_score=1.5,
                final_score=1.5,
                contributions=[
                    SphereContribution(
                        sphere="thinking_speech_learning",
                        source="activation",
                        source_id="act1",
                        amount=0.5,
                        evidence="Activation Mercury bonus",
                    )
                ]
            )
        },
        top_signals=[],
        top_activations=[],
    )

    evidences = service.get_evidence_for_sphere(
        backend_sphere_key="thinking_speech_learning",
        activation_layer=empty_activation_layer,
        scoring_result=scoring_result,
    )

    assert len(evidences) == 2
    assert evidences[0].kind == "activation"
    assert evidences[0].activation_id == "act1"
    assert evidences[1].kind == "score_contribution"
    assert evidences[1].contribution_source_id == "act1"

def test_audit_canon_versions_only_contains_strings(empty_activation_layer):
    service = SemanticV2Service()
    block = service.build_v2_block(activation_layer=empty_activation_layer)
    assert block.audit.canon_versions
    for k, v in block.audit.canon_versions.items():
        assert isinstance(k, str)
        assert isinstance(v, str)

def test_techniques_list_is_sorted(empty_activation_layer):
    service = SemanticV2Service()
    empty_activation_layer.activations.extend([
        ActivationEvidence(
            id="act_profection",
            technique="annual_profection",
            technique_family="profection",
            target_type="planet",
            target_key="MERCURY",
            kind="lord_of_year",
            strength=0.75,
            evidence="Mercury is lord of year",
        ),
        ActivationEvidence(
            id="act_transit",
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="MERCURY",
            kind="aspect",
            strength=0.8,
            evidence="Transit Moon opposition natal Mercury",
        ),
    ])
    block = service.build_v2_block(activation_layer=empty_activation_layer)
    target = block.activation_summary.top_activated_targets[0]
    assert target.techniques == ["annual_profection", "transit_to_natal"]
