"""API boundary tests for W3.3 firdar activations.

Tests that ActivationLayerService.build(sidecar_activation_layer=<dict>)
accepts firdar activations alongside transit and profection activations."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_3_layer_dict() -> dict:
    """Build a dict with transit (W3.1) + profection (W3.2) + firdar (W3.3) activations."""
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
                "applying": False,
                "phase": "separating",
                "strength": 0.75,
                "polarity": "tense",
                "evidence": "Transit Moon opposition natal Pluto, orb 1.0454°",
                "debug": {},
            },
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
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.75,
                "evidence": "Annual profection activates house 10",
                "debug": {},
            },
            {
                "id": "firdar_major__PERIOD_LORD__SUN",
                "technique": "firdar_major",
                "technique_family": "firdar",
                "target_type": "planet",
                "target_key": "SUN",
                "kind": "major_period_lord",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "target_planet": "SUN",
                "active_from": "2019-10-30",
                "exact_at": None,
                "active_until": "2029-10-29",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.65,
                "evidence": "Sun is major firdar lord on 2026-07-08",
                "debug": {"major_lord": "SUN", "age_years": 45.68767123},
            },
            {
                "id": "firdar_minor__SUBPERIOD_LORD__SATURN",
                "technique": "firdar_minor",
                "technique_family": "firdar",
                "target_type": "planet",
                "target_key": "SATURN",
                "kind": "minor_period_lord",
                "active": True,
                "source_frame": "natal",
                "target_frame": "natal",
                "target_planet": "SATURN",
                "active_from": "2025-07-18",
                "exact_at": None,
                "active_until": "2026-12-21",
                "phase": "period",
                "polarity": "neutral",
                "strength": 0.40,
                "evidence": "Saturn is minor firdar lord on 2026-07-08",
                "debug": {"minor_lord": "SATURN", "major_lord": "SUN"},
            },
        ],
        "by_planet": {
            "PLUTO": ["t2n__MOON__OPPOSITION__PLUTO"],
            "SUN": ["firdar_major__PERIOD_LORD__SUN"],
            "SATURN": ["firdar_minor__SUBPERIOD_LORD__SATURN"],
        },
        "by_house": {
            "10": ["annual_profection__HOUSE__10"],
        },
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    }


class TestActivationLayerServiceAcceptFirdar:
    """ActivationLayerService accepts firdar activations via sidecar dict."""

    def test_accepts_firdar(self):
        """Firdar major and minor activations are accepted."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_3_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        assert result.activation_layer_version == "al-1.0"

        firdar = [a for a in result.activations if a.technique_family == "firdar"]
        assert len(firdar) == 2

        for a in firdar:
            assert a.target_type == "planet"
            assert a.source_frame == "natal"
            assert a.target_frame == "natal"
            assert a.phase == "period"
            assert a.polarity == "neutral"

        major = [a for a in firdar if a.technique == "firdar_major"]
        assert len(major) == 1
        assert major[0].strength == 0.65
        assert major[0].active_from == "2019-10-30"
        assert major[0].exact_at is None
        assert major[0].active_until == "2029-10-29"

        minor = [a for a in firdar if a.technique == "firdar_minor"]
        assert len(minor) == 1
        assert minor[0].strength == 0.40
        assert minor[0].active_from == "2025-07-18"
        assert minor[0].exact_at is None
        assert minor[0].active_until == "2026-12-21"

    def test_by_planet_references(self):
        """by_planet index refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_3_layer_dict(),
        )
        assert "SUN" in result.by_planet
        assert "SATURN" in result.by_planet
        assert result.by_planet["SUN"] == ["firdar_major__PERIOD_LORD__SUN"]
        assert result.by_planet["SATURN"] == ["firdar_minor__SUBPERIOD_LORD__SATURN"]

    def test_firdar_family_preserved(self):
        """technique_family=firdar is preserved through validation."""
        result = ActivationLayerService().build(
            natal_context={},
            transits={},
            day_signals=[],
            target_date=date(2026, 7, 8),
            target_time="12:00",
            target_tz="Europe/Moscow",
            house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_3_layer_dict(),
        )
        for a in result.activations:
            if a.id.startswith("firdar"):
                assert a.technique_family == "firdar"


def test_dangling_firdar_index_raises():
    """Dangling firdar index refs raise validation error."""
    bad_dict = _make_w3_3_layer_dict()
    bad_dict["by_planet"]["MARS"] = ["nonexistent_firdar_id"]
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
