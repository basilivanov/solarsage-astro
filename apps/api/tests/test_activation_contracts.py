"""Tests for activation contract schemas (ActivationEvidence, ActivationLayer)."""

import pytest
from pydantic import ValidationError

from app.schemas.activation import ActivationEvidence, ActivationLayer


def test_activation_evidence_minimal():
    """A minimal valid ActivationEvidence must be accepted."""
    ev = ActivationEvidence(
        id="act-001",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.87,
        evidence="Transit Moon opposition natal Pluto (orb 1.0°, strength 0.87)",
    )
    assert ev.id == "act-001"
    assert ev.active is True
    assert ev.phase == "background"
    assert ev.polarity == "neutral"
    assert ev.debug == {}


def test_activation_evidence_full():
    """A fully populated ActivationEvidence must be accepted."""
    ev = ActivationEvidence(
        id="act-002",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Sun",
        kind="aspect",
        active=True,
        source_planet="Transit_Saturn",
        source_frame="transit",
        target_planet="Sun",
        target_frame="natal",
        aspect="opposition",
        orb=0.3,
        applying=True,
        exact_at="2026-07-08T15:30:00Z",
        phase="applying",
        house=10,
        strength=0.96,
        polarity="tense",
        weight_hint=2.0,
        evidence="Transit Saturn opposition natal Sun (orb 0.3°, strength 0.96)",
        debug={"extra": "data"},
    )
    assert ev.strength == 0.96
    assert ev.polarity == "tense"
    assert ev.debug["extra"] == "data"


@pytest.mark.parametrize("bad_strength", [-0.1, 1.5])
def test_activation_evidence_rejects_out_of_range_strength(bad_strength):
    """Strength must be in [0.0, 1.0]."""
    with pytest.raises(ValidationError):
        ActivationEvidence(
            id="act-bad",
            technique="transit_to_natal",
            technique_family="transit",
            target_type="planet",
            target_key="Moon",
            kind="aspect",
            evidence="test",
            strength=bad_strength,
        )


def test_activation_layer_minimal():
    """A minimal valid ActivationLayer must be accepted."""
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="PLACIDUS",
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )
    assert layer.schema_version == "activation-layer.v1"
    assert layer.activation_layer_version == "al-1.0"


def test_activation_layer_with_activations():
    """ActivationLayer with activations and by-index references."""
    ev = ActivationEvidence(
        id="act-001",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.87,
        evidence="test",
    )
    layer = ActivationLayer(
        calculation_version="1",
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
        activations=[ev],
        by_planet={"Moon": ["act-001"]},
        by_house={},
        by_lot={},
        by_angle={},
    )
    assert len(layer.activations) == 1
    assert layer.by_planet["Moon"] == ["act-001"]
    assert layer.by_house == {}
