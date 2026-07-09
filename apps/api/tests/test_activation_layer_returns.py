"""API boundary tests for W3.4 return activations."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_4_layer_dict() -> dict:
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
                "id": "solar_return__ANGLE_ASC__NATAL_HOUSE_3",
                "technique": "solar_return",
                "technique_family": "return",
                "target_type": "house",
                "target_key": "3",
                "kind": "return_angle_in_natal_house",
                "active": True,
                "source_frame": "solar_return",
                "target_frame": "natal",
                "house": 3,
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.70,
                "evidence": "Solar Return ASC falls in natal house 3",
                "debug": {
                    "return_type": "solar",
                    "return_jd": 2461344.34,
                    "return_utc_iso": "2026-10-30T20:17:07+00:00",
                    "target_jd": 2461229.5,
                    "return_location_policy": "current_location_if_known_else_birth_location",
                    "return_location_source": "birth_location",
                    "return_location_reason": "current_location_missing",
                    "return_lat": 67.94,
                    "return_lon": 32.81,
                    "return_tz": "Europe/Moscow",
                    "resolved_house_system": "WHOLE_SIGN",
                },
            },
            {
                "id": "solar_return__CHART_RULER__MARS",
                "technique": "solar_return",
                "technique_family": "return",
                "target_type": "planet",
                "target_key": "MARS",
                "kind": "return_chart_ruler",
                "active": True,
                "source_frame": "solar_return",
                "target_frame": "natal",
                "target_planet": "MARS",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.70,
                "evidence": "Mars is Solar Return chart ruler",
                "debug": {
                    "return_type": "solar",
                    "return_jd": 2461344.34,
                    "return_utc_iso": "2026-10-30T20:17:07+00:00",
                    "target_jd": 2461229.5,
                    "return_location_policy": "current_location_if_known_else_birth_location",
                    "return_location_source": "birth_location",
                    "return_location_reason": "current_location_missing",
                    "return_lat": 67.94,
                    "return_lon": 32.81,
                    "return_tz": "Europe/Moscow",
                    "resolved_house_system": "WHOLE_SIGN",
                },
            },
            {
                "id": "lunar_return__MOON_HOUSE__7",
                "technique": "lunar_return",
                "technique_family": "return",
                "target_type": "house",
                "target_key": "7",
                "kind": "return_moon_house",
                "active": True,
                "source_frame": "lunar_return",
                "target_frame": "lunar_return",
                "house": 7,
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.60,
                "evidence": "Lunar Return Moon is in Lunar Return house 7",
                "debug": {
                    "return_type": "lunar",
                    "return_jd": 2461209.52,
                    "return_utc_iso": "2026-06-18T00:30:22+00:00",
                    "target_jd": 2461229.5,
                    "return_location_policy": "current_location_if_known_else_birth_location",
                    "return_location_source": "birth_location",
                    "return_location_reason": "current_location_missing",
                    "return_lat": 67.94,
                    "return_lon": 32.81,
                    "return_tz": "Europe/Moscow",
                    "resolved_house_system": "WHOLE_SIGN",
                },
            },
            {
                "id": "lunar_return__ANGLE_ASC__NATAL_HOUSE_4",
                "technique": "lunar_return",
                "technique_family": "return",
                "target_type": "house",
                "target_key": "4",
                "kind": "return_angle_in_natal_house",
                "active": True,
                "source_frame": "lunar_return",
                "target_frame": "natal",
                "house": 4,
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.55,
                "evidence": "Lunar Return ASC falls in natal house 4",
                "debug": {
                    "return_type": "lunar",
                    "return_jd": 2461209.52,
                    "return_utc_iso": "2026-06-18T00:30:22+00:00",
                    "target_jd": 2461229.5,
                    "return_location_policy": "current_location_if_known_else_birth_location",
                    "return_location_source": "birth_location",
                    "return_location_reason": "current_location_missing",
                    "return_lat": 67.94,
                    "return_lon": 32.81,
                    "return_tz": "Europe/Moscow",
                    "resolved_house_system": "WHOLE_SIGN",
                },
            },
        ],
        "by_house": {
            "3": ["solar_return__ANGLE_ASC__NATAL_HOUSE_3"],
            "7": ["lunar_return__MOON_HOUSE__7"],
            "4": ["lunar_return__ANGLE_ASC__NATAL_HOUSE_4"],
        },
        "by_planet": {
            "MARS": ["solar_return__CHART_RULER__MARS"],
        },
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    }


class TestActivationLayerServiceAcceptReturns:
    """ActivationLayerService accepts return activations via sidecar dict."""

    def test_accepts_returns(self):
        """Solar and lunar return activations are accepted."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_4_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        returns = [a for a in result.activations if a.technique_family == "return"]
        assert len(returns) == 4
        for a in returns:
            assert a.phase == "period"
            assert a.polarity == "neutral"

    def test_source_frame_preserved(self):
        """source_frame/target_frame preserved for return activations."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_4_layer_dict(),
        )
        for a in result.activations:
            if a.id == "solar_return__ANGLE_ASC__NATAL_HOUSE_3":
                assert a.source_frame == "solar_return"
                assert a.target_frame == "natal"
            if a.id == "lunar_return__MOON_HOUSE__7":
                assert a.source_frame == "lunar_return"
                assert a.target_frame == "lunar_return"

    def test_debug_preserved(self):
        """return_jd, timestamp, location policy survive validation."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_4_layer_dict(),
        )
        sr = [a for a in result.activations if a.id == "solar_return__ANGLE_ASC__NATAL_HOUSE_3"]
        assert len(sr) == 1
        assert sr[0].debug.get("return_jd") == 2461344.34
        assert sr[0].debug.get("return_utc_iso") == "2026-10-30T20:17:07+00:00"

    def test_indexes_valid(self):
        """by_house and by_planet refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_4_layer_dict(),
        )
        assert "3" in result.by_house
        assert "MARS" in result.by_planet


def test_dangling_return_index_raises():
    """Dangling return index ref raises validation error."""
    bad_dict = _make_w3_4_layer_dict()
    bad_dict["by_house"]["99"] = ["nonexistent_return_id"]
    with pytest.raises(ValueError, match="by_house"):
        ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=bad_dict,
        )
