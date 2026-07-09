"""Tests: Scoring V2 breakdown contract + inactive activation."""
import pytest
from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer, ActivationEvidence
from app.services.scoring_v2_service import ScoringV2Service


def test_final_score_equals_raw_or_capped():
    """Every sphere final_score equals raw_score or capped raw_score."""
    signals = [AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=0.5, kind="aspect")]
    acts = [
        ActivationEvidence(id=f"a{i}", technique="annual_profection",
                           technique_family="profection",
                           target_type="planet", target_key="MERCURY",
                           kind="lord_of_year", phase="period",
                           polarity="neutral", strength=0.5,
                           evidence=f"A{i}")
        for i in range(6)
    ]
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=acts,
        by_planet={"MERCURY": [a.id for a in acts]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    for key, ss in result.sphere_scores.items():
        if ss.dominance_capped:
            assert ss.final_score < ss.raw_score, f"{key}: capped but final >= raw"
        else:
            assert ss.final_score == ss.raw_score, f"{key}: not capped but final != raw"


def test_contribution_sources_valid():
    """Contribution sources are only base_signal, activation, convergence, cap."""
    signals = [AstroSignal(type="aspect", planet="Transit_Mercury", target_planet="Venus",
                            aspect_type="trine", orb=0.5, strength=0.5, kind="aspect")]
    acts = [
        ActivationEvidence(id="a1", technique="annual_profection",
                           technique_family="profection",
                           target_type="planet", target_key="MERCURY",
                           kind="lord_of_year", phase="period",
                           polarity="neutral", strength=0.75,
                           evidence="A1"),
        ActivationEvidence(id="a2", technique="transit_to_natal",
                           technique_family="transit",
                           target_type="planet", target_key="MERCURY",
                           kind="trine", aspect="trine", phase="separating",
                           polarity="supportive", strength=0.6,
                           evidence="A2"),
    ]
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=acts,
        by_planet={"MERCURY": ["a1", "a2"]},
        by_house={}, by_lot={}, by_angle={},
    )
    result = ScoringV2Service().score_day(signals, layer)
    valid_sources = {"base_signal", "activation", "convergence", "cap"}
    for key, ss in result.sphere_scores.items():
        for c in ss.contributions:
            assert c.source in valid_sources, f"{key}: invalid source {c.source}"


def test_inactive_activation_ignored():
    """Inactive activation must not contribute to sphere score or status."""
    signals = []
    layer = ActivationLayer(
        calculation_version="1", target_date="2026-07-08",
        target_time="12:00", target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[
            ActivationEvidence(
                id="inactive_mercury",
                technique="annual_profection",
                technique_family="profection",
                target_type="planet",
                target_key="MERCURY",
                kind="lord",
                active=False,
                phase="period",
                strength=1.0,
                polarity="supportive",
                evidence="inactive should not count",
            ),
        ],
        by_planet={"MERCURY": ["inactive_mercury"]},
        by_house={}, by_lot={}, by_angle={},
    )
    r = ScoringV2Service().score_day(signals, layer)
    sphere_key = "thinking_speech_learning"
    ss = r.sphere_scores.get(sphere_key)
    assert ss is not None
    assert ss.activation_score == 0.0, f"Expected 0 activation_score, got {ss.activation_score}"
    assert r.status_breakdown.get("activation_support_score", 0) == 0.0, \
        f"Expected 0 activation_support_score"
    assert r.status_breakdown.get("activation_tension_score", 0) == 0.0, \
        f"Expected 0 activation_tension_score"
    # No activation contribution for that id
    for c in ss.contributions:
        assert c.source_id != "inactive_mercury", "Inactive activation must not appear in contributions"


def test_missing_sphere_amount_modifier_raises():
    """Missing activation_polarity.sphere_amount_modifier.neutral raises KeyError."""
    from copy import deepcopy
    import app.services.scoring_v2_service as svc
    from app.services.scoring_v2_service import ScoringV2Service

    orig = deepcopy(svc._get_scoring_v2())
    mut = deepcopy(orig)
    del mut["activation_polarity"]["sphere_amount_modifier"]["neutral"]
    svc._SCORING_V2 = mut
    try:
        r = ScoringV2Service().score_day([], ActivationLayer(
            calculation_version="1", target_date="2026-07-08", target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            activations=[ActivationEvidence(id="test", technique="annual_profection",
                           technique_family="profection", target_type="planet",
                           target_key="MERCURY", kind="lord", phase="period",
                           strength=0.1, polarity="neutral", evidence="test")],
            by_planet={"MERCURY": ["test"]}, by_house={}, by_lot={}, by_angle={},
        ))
        raise AssertionError("Missing sphere_amount_modifier.neutral did not raise")
    except KeyError:
        pass
    finally:
        svc._SCORING_V2 = orig


def test_missing_status_support_modifier_raises():
    """Missing activation_polarity.status_support_modifier.neutral raises KeyError."""
    from copy import deepcopy
    import app.services.scoring_v2_service as svc

    orig = deepcopy(svc._get_scoring_v2())
    mut = deepcopy(orig)
    del mut["activation_polarity"]["status_support_modifier"]["neutral"]
    svc._SCORING_V2 = mut
    try:
        ScoringV2Service().score_day([], ActivationLayer(
            calculation_version="1", target_date="2026-07-08", target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            activations=[ActivationEvidence(id="test", technique="annual_profection",
                           technique_family="profection", target_type="planet",
                           target_key="MERCURY", kind="lord", phase="period",
                           strength=0.1, polarity="neutral", evidence="test")],
            by_planet={"MERCURY": ["test"]}, by_house={}, by_lot={}, by_angle={},
        ))
        raise AssertionError("Missing status_support_modifier.neutral did not raise")
    except KeyError:
        pass
    finally:
        svc._SCORING_V2 = orig


def test_missing_status_tension_modifier_raises():
    """Missing activation_polarity.status_tension_modifier.neutral raises KeyError."""
    from copy import deepcopy
    import app.services.scoring_v2_service as svc

    orig = deepcopy(svc._get_scoring_v2())
    mut = deepcopy(orig)
    del mut["activation_polarity"]["status_tension_modifier"]["neutral"]
    svc._SCORING_V2 = mut
    try:
        ScoringV2Service().score_day([], ActivationLayer(
            calculation_version="1", target_date="2026-07-08", target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            activations=[ActivationEvidence(id="test", technique="annual_profection",
                           technique_family="profection", target_type="planet",
                           target_key="MERCURY", kind="lord", phase="period",
                           strength=0.1, polarity="neutral", evidence="test")],
            by_planet={"MERCURY": ["test"]}, by_house={}, by_lot={}, by_angle={},
        ))
        raise AssertionError("Missing status_tension_modifier.neutral did not raise")
    except KeyError:
        pass
    finally:
        svc._SCORING_V2 = orig


def test_missing_convergence_curve_entry_raises():
    """Missing convergence_curve[3] raises KeyError for three-family convergence."""
    from copy import deepcopy
    import app.services.scoring_v2_service as svc

    orig = deepcopy(svc._get_scoring_v2())
    mut = deepcopy(orig)
    del mut["convergence_curve"][3]
    svc._SCORING_V2 = mut
    try:
        acts = [
            ActivationEvidence(id="p", technique="annual_profection", technique_family="profection",
                               target_type="planet", target_key="MERCURY", kind="lord",
                               phase="period", strength=0.1, polarity="supportive", evidence="p"),
            ActivationEvidence(id="t", technique="transit_to_natal", technique_family="transit",
                               target_type="planet", target_key="MERCURY", kind="trine",
                               phase="period", strength=0.1, polarity="supportive", evidence="t"),
            ActivationEvidence(id="f", technique="firdar_major", technique_family="firdar",
                               target_type="planet", target_key="MERCURY", kind="lord",
                               phase="period", strength=0.1, polarity="supportive", evidence="f"),
        ]
        layer = ActivationLayer(calculation_version="1", target_date="2026-07-08",
                                target_time="12:00", target_tz="Europe/Moscow",
                                house_system="WHOLE_SIGN", activations=acts,
                                by_planet={"MERCURY": ["p", "t", "f"]},
                                by_house={}, by_lot={}, by_angle={})
        ScoringV2Service().score_day([], layer)
        raise AssertionError("Missing convergence_curve[3] did not raise")
    except KeyError:
        pass
    finally:
        svc._SCORING_V2 = orig
