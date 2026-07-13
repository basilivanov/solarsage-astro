"""Tests for ActivationLayerService — W2 minimal activation layer."""

import json
import pytest
from datetime import date
from pathlib import Path

from app.schemas.normalization import AstroSignal
from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
FIXTURE_PATH = FIXTURE_DIR / "activation_layer_minimal.json"


@pytest.fixture
def sample_day_signals() -> list[AstroSignal]:
    return [
        AstroSignal(
            type="aspect",
            planet="Transit_Moon",
            target_planet="Pluto",
            aspect_type="opposition",
            orb=1.0454,
            strength=0.8693,
            phase="applying",
        ),
        AstroSignal(
            type="aspect",
            planet="Transit_Mars",
            target_planet="Moon",
            aspect_type="sextile",
            orb=0.7876,
            strength=0.8687,
        ),
        AstroSignal(
            type="aspect",
            planet="Transit_Moon",
            target_planet="Neptune",
            aspect_type="trine",
            orb=2.5315,
            strength=0.6836,
            phase="separating",
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Transit_Sun",
            house=1,
            strength=1.0,
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Transit_Moon",
            house=10,
            strength=1.0,
        ),
        AstroSignal(
            type="planet_in_house",
            planet="Transit_Mars",
            house=12,
            strength=1.0,
        ),
    ]


def test_activation_layer_service_builds_minimal(sample_day_signals):
    """Build an activation layer from day signals. Must include transit-to-natal
    aspects and transit-in-house activations."""
    service = ActivationLayerService()
    layer = service.build(
        natal_context={},
        transits={},
        day_signals=sample_day_signals,
        target_date=date(2026, 7, 8),
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="WHOLE_SIGN",
    )
    assert isinstance(layer, ActivationLayer)
    assert layer.activation_layer_version == "al-1.1"
    assert len(layer.activations) >= 6  # 3 aspects + 3 house activations
    for act in layer.activations:
        assert act.active_from is None
        assert act.exact_at is None
        assert act.active_until is None

    # Check transit Moon opposition natal Pluto activation
    pluto_acts = [a for a in layer.activations if a.target_key == "PLUTO"]
    assert len(pluto_acts) == 1
    act = pluto_acts[0]
    assert act.technique == "transit_to_natal"
    assert act.source_planet == "MOON"
    assert act.aspect == "opposition"
    assert act.polarity == "tense"
    assert "Transit Moon opposition natal Pluto" in act.evidence

    # Check transit-in-house activations
    house_acts = [a for a in layer.activations if a.kind == "planet_in_house"]
    assert len(house_acts) >= 3
    sun_house = next(a for a in house_acts if a.source_planet == "SUN")
    assert sun_house.house == 1
    assert sun_house.technique == "transit_planet_in_house"
    assert "Transit Sun in natal house 1" in sun_house.evidence

    # Check index maps
    assert "PLUTO" in layer.by_planet
    assert "1" in layer.by_house
    assert layer.by_lot == {}
    assert layer.by_angle == {}


def test_activation_layer_service_ids_are_deterministic(sample_day_signals):
    """Same signals must produce same activation ids."""
    service = ActivationLayerService()
    layer1 = service.build(
        natal_context={}, transits={}, day_signals=sample_day_signals,
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    layer2 = service.build(
        natal_context={}, transits={}, day_signals=sample_day_signals,
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    ids1 = {a.id for a in layer1.activations}
    ids2 = {a.id for a in layer2.activations}
    assert ids1 == ids2


def test_activation_layer_service_accepts_sidecar_layer(sample_day_signals):
    """When a valid sidecar layer is provided, it is returned as-is after validation."""
    service = ActivationLayerService()
    built = service.build(
        natal_context={}, transits={}, day_signals=sample_day_signals,
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    # Re-inject as if from sidecar
    layer2 = service.build(
        natal_context={}, transits={}, day_signals=[],
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
        sidecar_activation_layer=built.model_dump(mode="json"),
    )
    assert len(layer2.activations) == len(built.activations)
    assert layer2.activation_layer_version == "al-1.1"


def test_activation_layer_service_no_natal_background_contamination():
    """Only day-scored signals (transit_*) should produce activations, not static natal signals."""
    mixed_signals = [
        AstroSignal(type="aspect", planet="Transit_Moon", target_planet="Pluto",
                     aspect_type="opposition", orb=1.0, strength=0.9),
        AstroSignal(type="planet_in_house", planet="Sun", house=5, strength=1.0),  # natal
        AstroSignal(type="planet_in_house", planet="Transit_Mars", house=12, strength=1.0),
    ]
    service = ActivationLayerService()
    layer = service.build(
        natal_context={}, transits={}, day_signals=mixed_signals,
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    # Natal Sun must not appear
    for act in layer.activations:
        assert act.source_planet != "SUN" or act.kind != "planet_in_house"
    # Transit Mars in house 12 must appear
    mars_house = [a for a in layer.activations if a.source_planet == "MARS" and a.kind == "planet_in_house"]
    assert len(mars_house) >= 1


def test_activation_layer_service_rejects_non_transit_signals():
    """Non-transit (natal) signals must not produce activations even if passed to build()."""
    non_transit = [
        AstroSignal(type="aspect", planet="Sun", target_planet="Moon",
                     aspect_type="square", orb=1.0, strength=0.8),
        AstroSignal(type="planet_in_house", planet="Venus", house=5, strength=1.0),
    ]
    service = ActivationLayerService()
    layer = service.build(
        natal_context={}, transits={}, day_signals=non_transit,
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
    )
    assert len(layer.activations) == 0, "Non-transit signals must not produce activations"
    assert layer.by_planet == {}
    assert layer.by_house == {}


def test_activation_layer_service_timed_sidecar_parity():
    """W1.1: timed sidecar dict has all three timing fields preserved byte-for-byte."""
    service = ActivationLayerService()
    timed_sidecar_layer = {
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.1",
        "calculation_version": "ss-calc-1.2.0",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [
            {
                "id": "t2n__MOON__OPPOSITION__PLUTO",
                "technique": "transit_to_natal",
                "techniqueFamily": "transit",
                "targetType": "planet",
                "targetKey": "PLUTO",
                "kind": "opposition",
                "active": True,
                "sourcePlanet": "Moon",
                "sourceFrame": "transit",
                "targetPlanet": "Pluto",
                "targetFrame": "natal",
                "aspect": "opposition",
                "orb": 1.05,
                "applying": False,
                "activeFrom": "2026-07-07T21:00:00Z",
                "exactAt": "2026-07-08T05:00:00Z",
                "activeUntil": "2026-07-09T21:00:00Z",
                "phase": "separating",
                "strength": 0.72,
                "polarity": "tense",
                "evidence": "Transit Moon opposition natal Pluto, orb 1.05°",
                "debug": {
                    "timing": {
                        "selected_branch": "plus",
                        "selected_exact_longitude": 22.320514,
                        "occurrence_index": 0,
                        "exact_hits_in_window": ["2026-07-08T05:00:00Z"],
                        "warning_code": None,
                    }
                }
            },
            {
                "id": "annual_profection__HOUSE__10",
                "technique": "annual_profection",
                "techniqueFamily": "profection",
                "targetType": "house",
                "targetKey": "10",
                "kind": "profected_house",
                "active": True,
                "sourceFrame": "natal",
                "targetFrame": "natal",
                "house": 10,
                "activeFrom": "2025-10-30",
                "exactAt": None,
                "activeUntil": "2026-10-29",
                "phase": "period",
                "strength": 0.75,
                "polarity": "neutral",
                "evidence": "Annual profection activates house 10",
                "debug": {},
            },
        ],
        "by_planet": {"PLUTO": ["t2n__MOON__OPPOSITION__PLUTO"]},
        "by_house": {"10": ["annual_profection__HOUSE__10"]},
        "by_lot": {},
        "by_angle": {},
        "warnings": []
    }

    layer = service.build(
        natal_context={}, transits={}, day_signals=[],
        target_date=date(2026, 7, 8), target_time="12:00",
        target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
        sidecar_activation_layer=timed_sidecar_layer,
    )

    assert len(layer.activations) == 2
    act = layer.activations[0]
    assert act.id == "t2n__MOON__OPPOSITION__PLUTO"
    assert act.active_from == "2026-07-07T21:00:00Z"
    assert act.exact_at == "2026-07-08T05:00:00Z"
    assert act.active_until == "2026-07-09T21:00:00Z"
    assert act.phase == "separating"
    assert act.applying is False
    assert act.debug["timing"]["selected_branch"] == "plus"
    assert act.debug["timing"]["selected_exact_longitude"] == 22.320514
    period = layer.activations[1]
    assert period.active_from == "2025-10-30"
    assert period.exact_at is None
    assert period.active_until == "2026-10-29"
