"""Tests for scoring V2 contract schemas (ScoringV2Result, SphereScoreV2, SphereContribution)."""

import pytest
from pydantic import ValidationError

from app.schemas.scoring_v2 import ScoringV2Result, SphereScoreV2, SphereContribution
from app.schemas.activation import ActivationEvidence


def test_sphere_contribution_minimal():
    """A minimal SphereContribution must be accepted."""
    sc = SphereContribution(
        sphere="work_status_achievement",
        source="base_signal",
        source_id="sig-001",
        amount=3.5,
        evidence="Transit Mars trine Saturn",
    )
    assert sc.amount == 3.5
    assert sc.before is None
    assert sc.after is None


def test_sphere_score_v2_minimal():
    """A minimal SphereScoreV2 must be accepted."""
    score = SphereScoreV2(
        key="work",
        title="Работа",
        base_score=3.5,
        activation_score=0.0,
        convergence_bonus=0.0,
        raw_score=3.5,
        final_score=3.5,
        contributions=[
            SphereContribution(
                sphere="work_status_achievement",
                source="base_signal",
                source_id="sig-001",
                amount=3.5,
                evidence="Transit Mars trine Saturn",
            )
        ],
    )
    assert score.key == "work"
    assert score.dominance_capped is False
    assert score.normalized_score is None


def test_scoring_v2_result_minimal():
    """A minimal ScoringV2Result must be accepted."""
    result = ScoringV2Result(
        canon_versions={"spheres": "v1", "aspect_rules": "v1"},
        day_status="supportive",
        status_breakdown={"positive_score": 7.35, "negative_score": 4.93, "ratio": 1.49},
        sphere_scores={},
        top_signals=[],
        top_activations=[],
    )
    assert result.scoring_version == "ss-scoring-2.0"
    assert result.day_status == "supportive"


def test_scoring_v2_result_with_full_data():
    """ScoringV2Result with nested sphere scores and activations."""
    activation = ActivationEvidence(
        id="act-001",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.87,
        evidence="Transit Moon opposition natal Pluto",
    )
    contribution = SphereContribution(
        sphere="relationships_partnership",
        source="activation",
        source_id="act-001",
        amount=0.89,
        evidence="Activation Moon-Pluto",
    )
    sphere = SphereScoreV2(
        key="relationships",
        title="Отношения",
        base_score=0.0,
        activation_score=0.89,
        convergence_bonus=0.0,
        raw_score=0.89,
        final_score=0.89,
        contributions=[contribution],
    )
    result = ScoringV2Result(
        canon_versions={"spheres": "v1", "aspect_rules": "v1"},
        day_status="supportive",
        status_breakdown={"positive_score": 7.35, "negative_score": 4.93},
        sphere_scores={"relationships": sphere},
        top_signals=[],
        top_activations=[activation],
    )
    assert len(result.sphere_scores) == 1
    assert result.sphere_scores["relationships"].final_score == 0.89
    assert len(result.top_activations) == 1
