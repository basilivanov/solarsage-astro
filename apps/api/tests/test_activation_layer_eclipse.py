"""API boundary tests for W3.6 eclipse window activations."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_6_layer_dict() -> dict:
    return {
        "schema_version": "activation-layer.v1",
        "activation_layer_version": "al-1.0",
        "calculation_version": "1",
        "target_date": "2026-08-12",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "WHOLE_SIGN",
        "activations": [
            {
                "id": "eclipse_window__SOLAR__TOTAL__2026_08_12__CONJUNCTION__NATAL_SUN",
                "technique": "eclipse_window",
                "technique_family": "eclipse",
                "target_type": "planet",
                "target_key": "SUN",
                "kind": "solar_eclipse_window",
                "active": True,
                "source_frame": "eclipse",
                "target_frame": "natal",
                "target_planet": "SUN",
                "aspect": "conjunction",
                "orb": 1.0,
                "phase": "period",
                "polarity": "mixed",
                "strength": 0.4,
                "evidence": "Solar total eclipse conjunct natal Sun, orb 1.0°, eclipse 2026-08-12",
                "debug": {
                    "eclipse_kind": "solar",
                    "eclipse_type": "total",
                    "eclipse_retflag": 4,
                    "eclipse_jd": 2461265.24,
                    "eclipse_utc_iso": "2026-08-12T17:45:00+00:00",
                    "eclipse_date": "2026_08_12",
                    "days_delta": 0.0,
                    "days_before": 14,
                    "days_after": 14,
                    "eclipse_longitude": 140.0,
                    "target_longitude": 139.0,
                    "orb": 1.0,
                    "orb_to_natal": 3.0,
                    "orb_factor": 0.6667,
                    "window_factor": 1.0,
                    "base_strength": 0.55,
                    "resolved_house_system": "WHOLE_SIGN",
                },
            },
        ],
        "by_planet": {
            "SUN": ["eclipse_window__SOLAR__TOTAL__2026_08_12__CONJUNCTION__NATAL_SUN"],
        },
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    }


class TestActivationLayerServiceAcceptEclipse:
    """ActivationLayerService accepts eclipse_window activations via sidecar dict."""

    def test_accepts_eclipse(self):
        """Eclipse_window activation is accepted."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 8, 12), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_6_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        ecl = [a for a in result.activations if a.technique_family == "eclipse"]
        assert len(ecl) == 1
        e = ecl[0]
        assert e.technique == "eclipse_window"
        assert e.target_key == "SUN"
        assert e.aspect == "conjunction"
        assert e.polarity == "mixed"
        assert e.phase == "period"
        assert e.source_frame == "eclipse"

    def test_debug_preserved(self):
        """Eclipse debug fields survive validation."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 8, 12), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_6_layer_dict(),
        )
        e = [a for a in result.activations if a.technique_family == "eclipse"][0]
        assert e.debug.get("eclipse_kind") == "solar"
        assert e.debug.get("eclipse_type") == "total"
        assert e.debug.get("eclipse_jd") == 2461265.24

    def test_index_valid(self):
        """by_planet refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 8, 12), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_6_layer_dict(),
        )
        assert "SUN" in result.by_planet


def test_dangling_eclipse_index_raises():
    """Dangling eclipse index ref raises validation error."""
    bad_dict = _make_w3_6_layer_dict()
    bad_dict["by_planet"]["MARS"] = ["nonexistent_eclipse_id"]
    with pytest.raises(ValueError, match="by_planet"):
        ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 8, 12), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=bad_dict,
        )
