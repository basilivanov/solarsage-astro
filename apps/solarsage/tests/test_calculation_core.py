# ############################################################################
# AI_HEADER: TEST_CALCULATION_CORE — direct versus HTTP calculation parity.
# ROLE: Proves offline replay and sidecar routes serialize identical results.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-CALCULATION-CORE
# purpose: Compare shared in-process calculations with their HTTP facades.
# owns:
#   - apps/solarsage/tests/test_calculation_core.py
# inputs: deterministic birth and target fixtures.
# outputs: pytest parity assertions.
# dependencies: FastAPI TestClient; calculation_core.
# side_effects: none.
# emitted_logs: none.
# invariants: direct and HTTP JSON payloads are equal for identical inputs.
# failure_policy: tests fail on any parity drift.
# END_MODULE_CONTRACT: M-TEST-CALCULATION-CORE

# START_MODULE_MAP: M-TEST-CALCULATION-CORE
# public_entrypoints: none
# semantic_blocks:
#   - PARITY: natal, transit, and activation-layer parity tests.
# owned_tests:
#   - apps/solarsage/tests/test_calculation_core.py
# END_MODULE_MAP: M-TEST-CALCULATION-CORE

from __future__ import annotations

from fastapi.testclient import TestClient
import pytest

pytestmark = pytest.mark.usefixtures("moshier_mode")

from solarsage.app import app
from solarsage.services.calculation_core import (
    calculate_activation_layer,
    calculate_natal_response,
    calculate_transits_response,
    prepare_natal_context,
    prepare_target_context,
)
from solarsage.services.transit_timing import TransitTimingSolver


client = TestClient(app)


# START_BLOCK: PARITY
def test_natal_direct_equals_http() -> None:
    kwargs = {
        "birth_date": "1990-01-15",
        "birth_time": "14:30",
        "birth_lat": 55.7558,
        "birth_lon": 37.6173,
        "birth_tz": "Europe/Moscow",
    }
    direct = calculate_natal_response(**kwargs).model_dump(mode="json")
    response = client.post("/v1/natal", json=kwargs)
    assert response.status_code == 200
    assert response.json() == direct


def test_transits_direct_equals_http() -> None:
    kwargs = {
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
    }
    direct = calculate_transits_response(**kwargs).model_dump(mode="json")
    response = client.post("/v1/transits", json=kwargs)
    assert response.status_code == 200
    assert response.json() == direct


def test_activation_layer_direct_equals_http() -> None:
    kwargs = {
        "birth_date": "1980-10-30",
        "birth_time": "19:50",
        "birth_lat": 67.9394,
        "birth_lon": 32.8144,
        "birth_tz": "Europe/Moscow",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "techniques": ["transit_to_natal", "firdar_major", "firdar_minor"],
    }
    direct = calculate_activation_layer(**kwargs).model_dump(mode="json")
    response = client.post(
        "/v1/activation-layer",
        json={
            "birth": {
                "date": kwargs["birth_date"],
                "time": kwargs["birth_time"],
                "lat": kwargs["birth_lat"],
                "lon": kwargs["birth_lon"],
                "tz": kwargs["birth_tz"],
            },
            "target": {
                "date": kwargs["target_date"],
                "time": kwargs["target_time"],
                "tz": kwargs["target_tz"],
            },
            "house_system": kwargs["house_system"],
            "techniques": kwargs["techniques"],
        },
    )
    assert response.status_code == 200
    assert response.json()["activation_layer"] == direct


def test_convergence_timing_scope_preserves_relevant_timing_and_raw_facts() -> None:
    kwargs = {
        "birth_date": "1980-10-30",
        "birth_time": "19:50",
        "birth_lat": 67.9394,
        "birth_lon": 32.8144,
        "birth_tz": "Europe/Moscow",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "techniques": ["transit_to_natal", "transit_to_angle", "transit_to_lot"],
    }
    full = calculate_activation_layer(**kwargs)
    scoped = calculate_activation_layer(**kwargs, timing_scope="convergence_eligible")
    full_by_id = {item.id: item for item in full.activations}
    scoped_by_id = {item.id: item for item in scoped.activations}

    assert scoped_by_id.keys() == full_by_id.keys()
    timed = 0
    deferred = 0
    for activation_id, scoped_item in scoped_by_id.items():
        full_item = full_by_id[activation_id]
        max_orb = float(scoped_item.debug["max_orb"])
        aspect_weight = float(scoped_item.debug["aspect_weight"])
        is_eligible = aspect_weight >= 0.55 and scoped_item.orb / max_orb <= 0.5
        if is_eligible:
            timed += 1
            assert scoped_item.active_from == full_item.active_from
            assert scoped_item.exact_at == full_item.exact_at
            assert scoped_item.active_until == full_item.active_until
            assert scoped_item.phase == full_item.phase
        else:
            deferred += 1
            assert scoped_item.active_from is None
            assert scoped_item.exact_at is None
            assert scoped_item.active_until is None
            assert scoped_item.debug["timing"]["status"] == "not_requested"

    assert timed > 0
    assert deferred > timed


def test_precomputed_contexts_preserve_activation_output() -> None:
    kwargs = {
        "birth_date": "1980-10-30",
        "birth_time": "19:50",
        "birth_lat": 67.9394,
        "birth_lon": 32.8144,
        "birth_tz": "Europe/Moscow",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "techniques": ["transit_to_natal", "transit_to_angle", "firdar_major"],
        "timing_scope": "convergence_eligible",
    }
    expected = calculate_activation_layer(**kwargs).model_dump(mode="json")
    natal_context = prepare_natal_context(
        **{key: kwargs[key] for key in (
            "birth_date",
            "birth_time",
            "birth_lat",
            "birth_lon",
            "birth_tz",
            "house_system",
        )}
    )
    target_context = prepare_target_context(
        **{key: kwargs[key] for key in ("target_date", "target_time", "target_tz")}
    )
    actual = calculate_activation_layer(
        **kwargs,
        natal_context=natal_context,
        target_context=target_context,
    ).model_dump(mode="json")

    assert actual == expected


def test_shared_target_timing_workspace_preserves_control_point_output() -> None:
    """Offline reuse changes cache hits only, never serialized evidence."""
    common = {
        "birth_date": "1980-10-30",
        "birth_lat": 67.9394,
        "birth_lon": 32.8144,
        "birth_tz": "Europe/Moscow",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
        "techniques": ["transit_to_natal"],
        "timing_scope": "convergence_eligible",
    }
    target_context = prepare_target_context(
        target_date=common["target_date"],
        target_time=common["target_time"],
        target_tz=common["target_tz"],
    )
    controls = []
    expected = []
    for birth_time in ("18:00", "21:00"):
        natal_context = prepare_natal_context(
            birth_date=common["birth_date"],
            birth_time=birth_time,
            birth_lat=common["birth_lat"],
            birth_lon=common["birth_lon"],
            birth_tz=common["birth_tz"],
            house_system=common["house_system"],
        )
        controls.append((birth_time, natal_context))
        expected.append(
            calculate_activation_layer(
                **common,
                birth_time=birth_time,
                natal_context=natal_context,
                target_context=target_context,
            ).model_dump(mode="json")
        )

    workspace = TransitTimingSolver(target_jd=target_context.target_jd)
    actual = [
        calculate_activation_layer(
            **common,
            birth_time=birth_time,
            natal_context=natal_context,
            target_context=target_context,
            timing_solver=workspace,
        ).model_dump(mode="json")
        for birth_time, natal_context in controls
    ]

    assert actual == expected
    assert workspace.cache.cache_hits > workspace.cache.cache_misses
# END_BLOCK: PARITY
