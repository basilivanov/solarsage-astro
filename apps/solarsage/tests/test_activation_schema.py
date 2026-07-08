"""Tests for sidecar activation schemas."""

import pytest
from pydantic import ValidationError

from solarsage.schemas.activation import ActivationEvidence, ActivationLayer


def test_sidecar_activation_evidence_minimal():
    ev = ActivationEvidence(
        id="act-001",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.5,
        evidence="test evidence",
    )
    assert ev.id == "act-001"
    assert ev.strength == 0.5


def test_sidecar_activation_layer_minimal():
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


@pytest.mark.parametrize("bad_strength", [-0.1, 1.5])
def test_sidecar_activation_evidence_rejects_out_of_range_strength(bad_strength):
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
