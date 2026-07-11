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
    assert ev.active_from is None
    assert ev.exact_at is None
    assert ev.active_until is None


def test_sidecar_activation_evidence_full():
    ev = ActivationEvidence(
        id="act-002",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.5,
        evidence="test evidence",
        active_from="2026-07-03T00:00:00Z",
        exact_at="2026-07-10T11:32:00Z",
        active_until="2026-07-18T00:00:00Z",
    )
    assert ev.active_from == "2026-07-03T00:00:00Z"
    assert ev.exact_at == "2026-07-10T11:32:00Z"
    assert ev.active_until == "2026-07-18T00:00:00Z"

    # round-trip via model dump
    dumped = ev.model_dump()
    assert dumped["active_from"] == "2026-07-03T00:00:00Z"
    assert dumped["exact_at"] == "2026-07-10T11:32:00Z"
    assert dumped["active_until"] == "2026-07-18T00:00:00Z"


def test_sidecar_activation_layer_minimal():
    layer = ActivationLayer(
        calculation_version="ss-calc-1.1.0",
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


def test_sidecar_activation_layer_rejects_missing_index_reference():
    ev = ActivationEvidence(
        id="act-001",
        technique="transit_to_natal",
        technique_family="transit",
        target_type="planet",
        target_key="Moon",
        kind="aspect",
        strength=0.5,
        evidence="test",
    )
    with pytest.raises(ValidationError, match="missing-id"):
        ActivationLayer(
            calculation_version="ss-calc-1.1.0",
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            activations=[ev],
            by_planet={"Moon": ["missing-id"]},
            by_house={},
            by_lot={},
            by_angle={},
        )
