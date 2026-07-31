# ############################################################################
# AI_HEADER: TEST_ACTIVATION_TARGET_SPEED — calculation-core target-speed tests.
# ROLE: Proves core-level target-speed enrichment preserves direct and grid parity.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-SIDECAR-ACTIVATION-TARGET-SPEED
# purpose: Verify target-speed debug enrichment at the GRACE-clean calculation-core boundary.
# owns:
#   - apps/solarsage/tests/test_activation_target_speed.py
# inputs: Prepared natal context and a builder-produced activation layer.
# outputs: Assertions for planet-target speed and non-planet exclusions.
# dependencies: solarsage.services.calculation_core and sidecar activation schemas.
# side_effects: none.
# emitted_logs: none.
# invariants: target speed is abs(natal target speed) / 24 for planets only.
# failure_policy: pytest failure on missing or fabricated speed metadata.
# END_MODULE_CONTRACT: M-TEST-SIDECAR-ACTIVATION-TARGET-SPEED

# START_MODULE_MAP: M-TEST-SIDECAR-ACTIVATION-TARGET-SPEED
# public_entrypoints:
#   - test_calculation_core_enriches_only_planet_target_speed
# semantic_blocks:
#   - TARGET_SPEED: target-speed debug semantics for transit evidence.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-SIDECAR-ACTIVATION-TARGET-SPEED

from __future__ import annotations

from dataclasses import replace

import pytest

from solarsage.schemas.activation import ActivationEvidence, ActivationLayer
from solarsage.services import calculation_core
from solarsage.services import activation_builder as builder


def _layer() -> ActivationLayer:
    common = {
        "technique_family": "transit",
        "source_planet": "Sun",
        "kind": "conjunction",
        "aspect": "conjunction",
        "orb": 0.1,
        "phase": "exact",
        "strength": 1.0,
        "polarity": "mixed",
        "evidence": "test",
        "debug": {},
    }
    return ActivationLayer(
        calculation_version="ss-calc-1.3.0",
        activation_layer_version="activation-layer-1.0.0",
        target_date="2026-07-31",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="PLACIDUS",
        activations=[
            ActivationEvidence(
                id="planet",
                technique="transit_to_natal",
                target_type="planet",
                target_key="MOON",
                target_planet="MOON",
                **common,
            ),
            ActivationEvidence(
                id="angle",
                technique="transit_to_angle",
                target_type="angle",
                target_key="ASC",
                angle="ASC",
                **common,
            ),
            ActivationEvidence(
                id="lot",
                technique="transit_to_lot",
                target_type="lot",
                target_key="FORTUNE",
                lot="FORTUNE",
                **common,
            ),
        ],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    )


def test_calculation_core_enriches_only_planet_target_speed(monkeypatch: pytest.MonkeyPatch) -> None:
    natal_context = builder.NatalCalculationContext(
        birth_date="1990-01-15",
        birth_time="14:30",
        birth_lat=55.75,
        birth_lon=37.62,
        birth_tz="Europe/Moscow",
        requested_house_system="PLACIDUS",
        natal_jd=1.0,
        natal_positions=({"name": "Moon", "longitude": 100.0, "speed": -2.4},),
        natal_houses_raw=(),
        natal_special_points=(),
        resolved_house_system="PLACIDUS",
        natal_by_name={"Moon": {"name": "Moon", "longitude": 100.0, "speed": -2.4}},
        natal_sun_house=None,
        sun_altitude_deg=10.0,
        is_day=True,
        sect_polar_condition=None,
        angles={"ASC": 100.0},
        lots=({"name": "FORTUNE", "longitude": 100.0, "house": 1, "formula": "test"},),
    )
    calls: list[dict] = []

    def build(**kwargs):
        calls.append(kwargs)
        return _layer()

    monkeypatch.setattr(calculation_core, "build_activation_layer", build)
    result = calculation_core.calculate_activation_layer(
        birth_date="1990-01-15",
        birth_time="14:30",
        birth_lat=55.75,
        birth_lon=37.62,
        birth_tz="Europe/Moscow",
        target_date="2026-07-31",
        target_time="12:00",
        target_tz="Europe/Moscow",
        techniques=["transit_to_natal", "transit_to_angle", "transit_to_lot"],
        natal_context=natal_context,
    )

    assert len(calls) == 1
    assert calls[0]["natal_context"] is natal_context
    by_id = {activation.id: activation for activation in result.activations}
    assert by_id["planet"].debug["target_speed_deg_per_hour"] == pytest.approx(0.1)
    assert "target_speed_deg_per_hour" not in by_id["angle"].debug
    assert "target_speed_deg_per_hour" not in by_id["lot"].debug
    for speed in (None, float("nan")):
        missing_speed_context = replace(
            natal_context,
            natal_by_name={"Moon": {"name": "Moon", "longitude": 100.0, "speed": speed}},
        )
        missing_speed_result = calculation_core.calculate_activation_layer(
            birth_date="1990-01-15",
            birth_time="14:30",
            birth_lat=55.75,
            birth_lon=37.62,
            birth_tz="Europe/Moscow",
            target_date="2026-07-31",
            target_time="12:00",
            target_tz="Europe/Moscow",
            techniques=["transit_to_natal"],
            natal_context=missing_speed_context,
        )
        assert "target_speed_deg_per_hour" not in missing_speed_result.activations[0].debug
