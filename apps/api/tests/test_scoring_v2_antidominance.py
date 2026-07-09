"""Tests: Scoring V2 anti-dominance cap."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def test_five_activations_one_sphere_cap_applies():
    """Five activations on one sphere apply dominance cap."""
    signals = [
        AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                     aspect_type="trine", orb=0.5, strength=0.5, kind="aspect"),
    ]
    acts = [
        ActivationEvidence(id=f"act_{i}", technique="annual_profection",
                           technique_family="profection",
                           target_type="planet", target_key="MERCURY",
                           kind="lord_of_year", phase="period",
                           polarity="neutral", strength=1.0,
                           evidence=f"Test activation {i}")
        for i in range(5)
    ]
    # But they all have the same family, so convergence will be 0
    # To trigger dominance cap, we need different families
    families = ["profection", "transit", "firdar", "return", "progression"]
    acts2 = []
    for i, fam in enumerate(families):
        acts2.append(ActivationEvidence(
            id=f"div_act_{i}", technique=f"{fam}_test",
            technique_family=fam,
            target_type="planet", target_key="MERCURY",
            kind="test", phase="period",
            polarity="supportive", strength=1.0,
            evidence=f"Family {fam} activation",
        ))
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08", target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
        activations=acts2,
        by_planet={"MERCURY": [a.id for a in acts2]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    sphere_key = "thinking_speech_learning"
    ss = result.sphere_scores[sphere_key]
    assert ss.dominance_capped, "Expected dominance cap applied"
    cap_contributions = [c for c in ss.contributions if c.source == "cap"]
    assert len(cap_contributions) >= 1, "Expected cap contribution"
    assert cap_contributions[0].amount < 0, "Cap contribution should be negative"
    assert ss.final_score < ss.raw_score, "Final score should be lower after cap"
