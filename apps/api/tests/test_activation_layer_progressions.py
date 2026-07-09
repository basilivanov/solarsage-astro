"""API boundary tests for W3.5 progression activations."""
from __future__ import annotations

from datetime import date

import pytest

from app.schemas.activation import ActivationLayer
from app.services.activation_layer_service import ActivationLayerService


def _make_w3_5_layer_dict() -> dict:
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
                "id": "solar_arc__SUN__CONJUNCTION__NATAL_MERCURY",
                "technique": "solar_arc",
                "technique_family": "progression",
                "target_type": "planet",
                "target_key": "MERCURY",
                "kind": "solar_arc_aspect",
                "active": True,
                "source_frame": "solar_arc",
                "target_frame": "natal",
                "target_planet": "MERCURY",
                "aspect": "conjunction",
                "orb": 0.5,
                "phase": "period",
                "polarity": "mixed",
                "strength": 0.5,
                "evidence": "Solar Arc Sun conjunction natal Mercury, orb 0.5°",
                "debug": {"progression_method": "solar_arc", "birth_jd": 2444543.2, "target_jd": 2461229.5, "age_years": 45.68, "progressed_jd": 2444588.88, "progressed_utc_iso": "1981-01-01T00:00:00+00:00", "max_orb": 1.0, "resolved_house_system": "WHOLE_SIGN", "solar_arc_delta": 45.5},
            },
            {
                "id": "secondary_progression__MOON__SQUARE__NATAL_SUN",
                "technique": "secondary_progression",
                "technique_family": "progression",
                "target_type": "planet",
                "target_key": "SUN",
                "kind": "progressed_moon_aspect",
                "active": True,
                "source_frame": "progressed",
                "target_frame": "natal",
                "target_planet": "SUN",
                "aspect": "square",
                "orb": 0.7,
                "phase": "period",
                "polarity": "tense",
                "strength": 0.4,
                "evidence": "Progressed Moon square natal Sun, orb 0.7°",
                "debug": {"progression_method": "secondary_progression", "birth_jd": 2444543.2, "target_jd": 2461229.5, "age_years": 45.68, "progressed_jd": 2444588.88, "progressed_utc_iso": "1981-01-01T00:00:00+00:00", "max_orb": 1.0, "resolved_house_system": "WHOLE_SIGN"},
            },
        ],
        "by_planet": {
            "MERCURY": ["solar_arc__SUN__CONJUNCTION__NATAL_MERCURY"],
            "SUN": ["secondary_progression__MOON__SQUARE__NATAL_SUN"],
        },
        "by_house": {},
        "by_lot": {},
        "by_angle": {},
        "warnings": [],
    }


class TestActivationLayerServiceAcceptProgressions:
    """ActivationLayerService accepts progression activations via sidecar dict."""

    def test_accepts_both_progressions(self):
        """Solar arc and secondary progression activations are accepted."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_5_layer_dict(),
        )
        assert isinstance(result, ActivationLayer)
        progressions = [a for a in result.activations if a.technique_family == "progression"]
        assert len(progressions) == 2

    def test_fields_preserved(self):
        """ID, technique, family, kind, frames, aspect, orb, polarity, strength survive."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_5_layer_dict(),
        )
        sa = [a for a in result.activations if a.id == "solar_arc__SUN__CONJUNCTION__NATAL_MERCURY"]
        assert len(sa) == 1
        s = sa[0]
        assert s.technique == "solar_arc"
        assert s.technique_family == "progression"
        assert s.target_frame == "natal"
        assert s.source_frame == "solar_arc"
        assert s.aspect == "conjunction"
        assert s.orb == 0.5
        assert s.polarity == "mixed"
        assert s.strength == 0.5

        sp = [a for a in result.activations if a.id == "secondary_progression__MOON__SQUARE__NATAL_SUN"]
        assert len(sp) == 1
        s2 = sp[0]
        assert s2.technique == "secondary_progression"
        assert s2.technique_family == "progression"
        assert s2.aspect == "square"
        assert s2.orb == 0.7

    def test_debug_preserved(self):
        """Progression debug fields survive validation."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_5_layer_dict(),
        )
        sa = [a for a in result.activations if a.id == "solar_arc__SUN__CONJUNCTION__NATAL_MERCURY"]
        assert sa[0].debug.get("progression_method") == "solar_arc"
        assert sa[0].debug.get("birth_jd") == 2444543.2

    def test_indexes_valid(self):
        """by_planet refs point to existing activations."""
        result = ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=_make_w3_5_layer_dict(),
        )
        assert "MERCURY" in result.by_planet
        assert "SUN" in result.by_planet


def test_dangling_progression_index_raises():
    """Dangling progression index ref raises validation error."""
    bad_dict = _make_w3_5_layer_dict()
    bad_dict["by_planet"]["NEPTUNE"] = ["nonexistent_progression_id"]
    with pytest.raises(ValueError, match="by_planet"):
        ActivationLayerService().build(
            natal_context={}, transits={}, day_signals=[],
            target_date=date(2026, 7, 8), target_time="12:00",
            target_tz="Europe/Moscow", house_system="WHOLE_SIGN",
            sidecar_activation_layer=bad_dict,
        )
