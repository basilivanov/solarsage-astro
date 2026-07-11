"""API boundary tests for W3.2 profection activations.

Tests that ActivationLayerService.build(sidecar_activation_layer=<dict>)
accepts profection activations alongside transit activations."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_2_layer_dict() -> dict:
    """Build a dict with transit (W3.1) + profection (W3.2) activations."""
    return {
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "1",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [
            # W3.1 transit
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
                "applying": False,
                "phase": "separating",
                "strength": 0.75,
                "polarity": "tense",
                "evidence": "Transit Moon opposition natal Pluto, orb 1.0454°",
                "debug": {},
            },
            # W3.2 annual profection house
            {
                "id": "annual_profection__HOUSE__10",
                "technique": "annual_profection",
                "technique_family": "profection",
                "target_type": "house",
                "target_key": "10",
                "kind": "profected_house",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "house": 10,
                "active_from": "2025-10-30",
                "exact_at": None,
                "active_until": "2026-10-29",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.75,
                "evidence": "Annual profection activates house 10",
                "debug": {"age": 45, "ruler": "MARS"},
            },
            # W3.2 annual profection lord
            {
                "id": "annual_profection__LORD_OF_YEAR__MARS",
                "technique": "annual_profection",
                "technique_family": "profection",
                "target_type": "planet",
                "target_key": "MARS",
                "kind": "lord_of_year",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "target_planet": "MARS",
                "active_from": "2025-10-30",
                "exact_at": None,
                "active_until": "2026-10-29",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.75,
                "evidence": "Mars is lord of year for annual profection house 10",
                "debug": {"age": 45},
            },
            # W3.2 monthly profection house
            {
                "id": "monthly_profection__HOUSE__6",
                "technique": "monthly_profection",
                "technique_family": "profection",
                "target_type": "house",
                "target_key": "6",
                "kind": "monthly_profected_house",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "house": 6,
                "active_from": "2026-06-30",
                "exact_at": None,
                "active_until": "2026-07-29",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.45,
                "evidence": "Monthly profection activates house 6",
                "debug": {"completed_month_steps": 8, "ruler": "JUPITER"},
            },
            # W3.2 monthly profection lord
            {
                "id": "monthly_profection__LORD_OF_MONTH__JUPITER",
                "technique": "monthly_profection",
                "technique_family": "profection",
                "target_type": "planet",
                "target_key": "JUPITER",
                "kind": "lord_of_month",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "target_planet": "JUPITER",
                "active_from": "2026-06-30",
                "exact_at": None,
                "active_until": "2026-07-29",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.45,
                "evidence": "Jupiter is lord of month for monthly profection house 6",
                "debug": {"completed_month_steps": 8},
            },
        ],
        "by_planet": {
            "PLUTO": ["t2n__MOON__OPPOSITION__PLUTO"],
            "MARS": ["annual_profection__LORD_OF_YEAR__MARS"],
            "JUPITER": ["monthly_profection__LORD_OF_MONTH__JUPITER"],
        },
        "by_house": {
            "10": ["annual_profection__HOUSE__10"],
            "6": ["monthly_profection__HOUSE__6"],
        },
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    }


class TestActivationLayerServiceAcceptProfections:
    """ActivationLayerService accepts profection activations via sidecar dict."""

    def test_accepts_annual_profection(self):
        """annual_profection activations are accepted via sidecar dict."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_2_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        assert result.activation_layer_version == "al-1.0"
        assert len(result.activations) == 5  # 1 transit + 4 profection

        # Check profection activations preserved
        profections = [a for a in result.activations if a.technique_family == "profection"]
        assert len(profections) == 4

        for a in profections:
            assert a.phase == "period"
            assert a.polarity == "neutral"

        ann = [a for a in profections if a.technique == "annual_profection"]
        assert len(ann) == 2
        assert ann[0].strength == 0.75
        assert {a.active_from for a in ann} == {"2025-10-30"}
        assert {a.active_until for a in ann} == {"2026-10-29"}

        mon = [a for a in profections if a.technique == "monthly_profection"]
        assert len(mon) == 2
        assert mon[0].strength == 0.45
        assert {a.active_from for a in mon} == {"2026-06-30"}
        assert {a.active_until for a in mon} == {"2026-07-29"}

    def test_by_house_and_by_planet_references(self):
        """by_house and by_planet index refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_2_layer_dict(),
        )
        # Model validator already checks refs; verify data
        assert "10" in result.by_house
        assert "6" in result.by_house
        assert "MARS" in result.by_planet
        assert "JUPITER" in result.by_planet

    def test_debug_values_preserved(self):
        """Profection debug values pass through."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_2_layer_dict(),
        )
        ann_house = [a for a in result.activations if a.id == "annual_profection__HOUSE__10"]
        assert len(ann_house) == 1
        assert ann_house[0].debug.get("age") == 45
        assert ann_house[0].debug.get("ruler") == "MARS"

        mon_house = [a for a in result.activations if a.id == "monthly_profection__HOUSE__6"]
        assert len(mon_house) == 1
        assert mon_house[0].debug.get("completed_month_steps") == 8


def test_sidecar_dict_invalid_profection_index_raises():
    """A sidecar dict with dangling profection index refs is rejected."""
    bad_dict = _make_w3_2_layer_dict()
    bad_dict["by_house"]["99"] = ["nonexistent"]
    with pytest.raises(ValueError, match="by_house"):
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
