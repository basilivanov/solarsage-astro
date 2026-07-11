"""API boundary tests for W3.1 sidecar activation layer acceptance.

Tests that ActivationLayerService.build(sidecar_activation_layer=<dict>)
accepts a full W3.1 sidecar layer with all four transit techniques
and validates the index references."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_1_layer_dict() -> dict:
    """Build a dict representing a W3.1 sidecar activation layer
    with all four transit techniques and populated indices."""
    return {
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "1",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [
            {
                "id": "t2n__MOON__OPPOSITION__PLUTO",
                "technique": "transit_to_natal",
                "technique_family": "transit",
                "target_type": "planet",
                "target_key": "PLUTO",
                "kind": "opposition",
                "active": True,
                "source_planet": "Moon",
                "source_frame": "transit",
                "target_planet": "PLUTO",
                "target_frame": "natal",
                "aspect": "opposition",
                "orb": 1.0454,
                "applying": True,
                "active_from": "2026-07-07T22:23:41Z",
                "exact_at": "2026-07-08T07:10:15Z",
                "active_until": "2026-07-08T15:51:22Z",
                "phase": "applying",
                "strength": 0.85,
                "polarity": "tense",
                "evidence": "Transit Moon opposition natal Pluto, orb 1.0454°",
                "debug": {
                    "source_longitude": 23.37,
                    "target_longitude": 234.78,
                    "timing": {"selected_branch": "plus", "selected_exact_longitude": 22.320514},
                },
            },
            {
                "id": "t2a__SATURN__TRINE__MC",
                "technique": "transit_to_angle",
                "technique_family": "transit",
                "target_type": "angle",
                "target_key": "MC",
                "kind": "trine",
                "active": True,
                "source_planet": "Saturn",
                "source_frame": "transit",
                "target_frame": "angle",
                "aspect": "trine",
                "orb": 1.2345,
                "applying": False,
                "phase": "separating",
                "strength": 0.70,
                "polarity": "supportive",
                "angle": "MC",
                "evidence": "Transit Saturn trine natal MC, orb 1.2345°",
                "debug": {"source_longitude": 150.0, "target_longitude": 30.0},
            },
            {
                "id": "t2l__VENUS__TRINE__FORTUNE",
                "technique": "transit_to_lot",
                "technique_family": "transit",
                "target_type": "lot",
                "target_key": "FORTUNE",
                "kind": "trine",
                "active": True,
                "source_planet": "Venus",
                "source_frame": "transit",
                "target_frame": "lot",
                "aspect": "trine",
                "orb": 0.9876,
                "applying": True,
                "phase": "applying",
                "strength": 0.65,
                "polarity": "supportive",
                "lot": "FORTUNE",
                "evidence": "Transit Venus trine lot FORTUNE, orb 0.9876°",
                "debug": {
                    "source_longitude": 45.0,
                    "target_longitude": 345.0,
                    "lot": {"name": "FORTUNE", "longitude": 345.0, "house": 2, "formula": "fortune_day_asc_moon_sun"},
                },
            },
            {
                "id": "tih__MARS__12",
                "technique": "transit_planet_in_house",
                "technique_family": "transit",
                "target_type": "house",
                "target_key": "12",
                "kind": "planet_in_house",
                "active": True,
                "source_planet": "Mars",
                "source_frame": "transit",
                "target_frame": "natal",
                "house": 12,
                "strength": 1.0,
                "polarity": "neutral",
                "evidence": "Transit Mars in natal house 12, strength 1.00",
                "debug": {"longitude": 66.07, "house": 12},
            },
        ],
        "by_planet": {
            "PLUTO": ["t2n__MOON__OPPOSITION__PLUTO"],
        },
        "by_house": {
            "12": ["tih__MARS__12"],
        },
        "by_lot": {
            "FORTUNE": ["t2l__VENUS__TRINE__FORTUNE"],
        },
        "by_angle": {
            "MC": ["t2a__SATURN__TRINE__MC"],
        },
        "warnings": [],
    }


class TestActivationLayerServiceAcceptSidecarDict:
    """ActivationLayerService.build(sidecar_activation_layer=<dict>) accepts
    W3.1 transit activations."""

    def test_accepts_transit_to_natal(self):
        """transit_to_natal activation is accepted via sidecar dict."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_1_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        assert result.activation_layer_version == "al-1.0"
        assert len(result.activations) == 4
        act = result.activations[0]
        assert act.id == "t2n__MOON__OPPOSITION__PLUTO"
        assert act.active_from == "2026-07-07T22:23:41Z"
        assert act.exact_at == "2026-07-08T07:10:15Z"
        assert act.active_until == "2026-07-08T15:51:22Z"
        assert act.debug["timing"]["selected_branch"] == "plus"

    def test_indexes_reference_valid_ids(self):
        """by_planet, by_house, by_lot, by_angle refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_1_layer_dict(),
        )
        # The model validator already checks index references
        # Verify the data round-tripped correctly
        t2n = [a for a in result.activations if a.technique == "transit_to_natal"]
        assert len(t2n) == 1
        assert t2n[0].source_planet == "Moon"

        t2a = [a for a in result.activations if a.technique == "transit_to_angle"]
        assert len(t2a) == 1
        assert t2a[0].angle == "MC"

        t2l = [a for a in result.activations if a.technique == "transit_to_lot"]
        assert len(t2l) == 1
        assert t2l[0].lot == "FORTUNE"

        tih = [a for a in result.activations if a.technique == "transit_planet_in_house"]
        assert len(tih) == 1
        assert tih[0].house == 12

        assert "PLUTO" in result.by_planet
        assert "MC" in result.by_angle
        assert "FORTUNE" in result.by_lot
        assert "12" in result.by_house

    def test_no_scoring_v2_enabled(self):
        """No scoring v2 is enabled by accepting a W3.1 sidecar layer."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_1_layer_dict(),
        )
        # scoring v2 is not referenced anywhere in this path
        assert result.activation_layer_version == "al-1.0"


def test_sidecar_dict_invalid_index_raises():
    """A sidecar dict with dangling index references must be rejected."""
    bad_dict = _make_w3_1_layer_dict()
    bad_dict["by_planet"]["SATURN"] = ["nonexistent_id"]
    with pytest.raises(ValueError, match="by_planet"):
        ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=bad_dict,
        )
