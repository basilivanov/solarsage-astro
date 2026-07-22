import pytest
from datetime import date as Date
from app.core.versions import SCORING_V2_VERSION
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


@pytest.fixture
def empty_scoring_v2_result():
    """Minimal typed ScoringV2Result for tests that do not exercise scoring."""
    return ScoringV2Result(
        scoring_version=SCORING_V2_VERSION,
        canon_versions={"spheres": "v1"},
        day_status="steady",
        status_breakdown={},
        sphere_scores={},
        top_signals=[],
        top_activations=[],
    )


def test_semantic_v2_service_no_convergence(empty_activation_layer, empty_scoring_v2_result):
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
    block = service.build_v2_block(activation_layer=empty_activation_layer, scoring_result=empty_scoring_v2_result)
    assert block.activation_summary.headline == "День в основном определяется текущими транзитами, без сильной сходимости долгих техник."
    assert len(block.why_today) == 1
    assert block.why_today[0].id == "fallback-no-convergence"
    # Prove typed input was not mutated
    assert empty_scoring_v2_result.canon_versions == {"spheres": "v1"}

def test_semantic_v2_service_with_convergence(empty_activation_layer, empty_scoring_v2_result):
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
    block = service.build_v2_block(activation_layer=empty_activation_layer, scoring_result=empty_scoring_v2_result)
    assert "сходятся 2 независимые техники" in block.activation_summary.headline
    assert len(block.why_today) == 2
    assert {item.id for item in block.why_today} == {"why-planet-MERCURY-transit", "why-planet-MERCURY-profection"}
    # Prove typed input was not mutated
    assert empty_scoring_v2_result.canon_versions == {"spheres": "v1"}

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

def test_audit_canon_versions_only_contains_strings(empty_activation_layer, empty_scoring_v2_result):
    service = SemanticV2Service()
    block = service.build_v2_block(activation_layer=empty_activation_layer, scoring_result=empty_scoring_v2_result)
    assert block.audit.canon_versions
    for k, v in block.audit.canon_versions.items():
        assert isinstance(k, str)
        assert isinstance(v, str)

def test_techniques_list_is_sorted(empty_activation_layer, empty_scoring_v2_result):
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
    block = service.build_v2_block(activation_layer=empty_activation_layer, scoring_result=empty_scoring_v2_result)
    target = block.activation_summary.top_activated_targets[0]
    assert target.techniques == ["annual_profection", "transit_to_natal"]


def _activation(act_id: str, strength: float, evidence: str | None = None) -> ActivationEvidence:
    return ActivationEvidence(
        id=act_id,
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="SUN",
        kind="aspect",
        strength=strength,
        evidence=evidence or f"evidence {act_id}",
    )


def test_evidence_packet_caps_twelve_strongest_with_stable_tiebreak(empty_activation_layer):
    # 15 activations: the packet keeps at most 12 STRONGEST, strength desc,
    # id asc as the deterministic tie-break — never a random subset.
    acts = [_activation(f"act-{i:02d}", strength=round(0.05 * i, 2)) for i in range(1, 16)]
    layer = empty_activation_layer.model_copy(update={"activations": acts})
    contexts = []

    packet = SemanticV2Service().build_llm_evidence_packet(
        day_status="steady",
        activation_layer=layer,
        scoring_result=None,
        contexts=contexts,
    )

    top = packet["top_activations"]
    assert len(top) == 12
    assert [a["id"] for a in top] == [
        "act-15", "act-14", "act-13", "act-12", "act-11", "act-10",
        "act-09", "act-08", "act-07", "act-06", "act-05", "act-04",
    ]


def test_evidence_packet_tiebreak_is_deterministic_by_id(empty_activation_layer):
    acts = [
        _activation("z-last", 0.5),
        _activation("a-first", 0.5),
        _activation("m-mid", 0.5),
    ]
    layer = empty_activation_layer.model_copy(update={"activations": acts})
    packet = SemanticV2Service().build_llm_evidence_packet(
        day_status="steady", activation_layer=layer, scoring_result=None, contexts=[],
    )
    assert [a["id"] for a in packet["top_activations"]] == ["a-first", "m-mid", "z-last"]


def test_evidence_packet_row_titles_capped_at_three_unique(empty_activation_layer):
    contexts = [{
        "key": "work",
        "verdict": "good",
        "evidence": [
            {"title": "Аспект Солнца к Юпитеру"},
            {"title": "Солнце в 10 доме"},
            {"title": "Аспект Солнца к Юпитеру"},  # duplicate title — dedup
            {"title": "Луна усиливает фон"},
            {"title": "Меркурий поддерживает документы"},
        ],
    }]
    packet = SemanticV2Service().build_llm_evidence_packet(
        day_status="steady",
        activation_layer=empty_activation_layer,
        scoring_result=None,
        contexts=contexts,
    )
    rows = packet["concrete_rows"]
    assert len(rows) == 1
    assert rows[0]["evidence"] == [
        "Аспект Солнца к Юпитеру",
        "Солнце в 10 доме",
        "Луна усиливает фон",
    ]
