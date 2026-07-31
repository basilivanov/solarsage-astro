# ############################################################################
# AI_HEADER: TEST_ACTIVATION_GRID — shared birth-time activation-grid tests.
# ROLE: Proves strict grid validation, shared-context orchestration, direct parity,
#       and verified ephemeris artifact lineage.
# ############################################################################

# START_MODULE_CONTRACT: M-TEST-ACTIVATION-GRID
# purpose: Validate the internal sidecar activation grid without changing the single-layer contract.
# owns:
#   - apps/solarsage/tests/test_activation_grid.py
# inputs: Birth-time control grids, deterministic spies, and one real ephemeris parity fixture.
# outputs: Assertions for validation, reuse, order, solver policy, byte/value parity,
#   and artifact identity propagation.
# dependencies: M-SIDECAR-CALCULATION-CORE and sidecar activation schemas.
# side_effects: One real ephemeris calculation in the parity test; all other tests use spies.
# emitted_logs: none.
# invariants: no parallelism, no hidden cache, one target context per grid request,
#   and no artifact fallback in the endpoint.
# failure_policy: invalid grids raise ValueError before calculation; calculation failures propagate.
# END_MODULE_CONTRACT: M-TEST-ACTIVATION-GRID

# START_MODULE_MAP: M-TEST-ACTIVATION-GRID
# public_entrypoints:
#   - pytest test functions
# semantic_blocks:
#   - VALIDATION: strict one-to-seven minute grid validation.
#   - REUSE: target/natal context and timing-solver reuse in request order.
#   - PARITY: one-point grid equals direct convergence-scoped calculation.
# owned_tests:
#   - self
# END_MODULE_MAP: M-TEST-ACTIVATION-GRID

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest
import solarsage.api.activation_layer as activation_api
from fastapi.testclient import TestClient

from solarsage.app import app
from solarsage.core import versions
from solarsage.core import ephemeris_runtime
from solarsage.schemas.activation import ActivationLayer
from solarsage.services import calculation_core


pytestmark = pytest.mark.usefixtures("moshier_mode")
client = TestClient(app)


def _layer() -> ActivationLayer:
    return ActivationLayer(
        calculation_version=versions.CALCULATION_VERSION,
        activation_layer_version=versions.ACTIVATION_LAYER_VERSION,
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


def _grid_kwargs() -> dict:
    return {
        "birth_date": "1990-01-15",
        "birth_lat": 55.7558,
        "birth_lon": 37.6173,
        "birth_tz": "Europe/Moscow",
        "target_date": "2026-07-08",
        "target_time": "12:00",
        "target_tz": "Europe/Moscow",
        "house_system": "PLACIDUS",
    }


# START_BLOCK: VALIDATION
def test_birth_time_validator_is_public_and_preserves_order() -> None:
    assert calculation_core.validate_birth_time_grid(("00:00", "03:00")) == ("00:00", "03:00")


@pytest.mark.parametrize(
    "birth_times",
    [
        (),
        tuple(f"{hour:02d}:00" for hour in range(8)),
        ("03:00", "00:00"),
        ("00:00", "00:00"),
        ("1:00",),
        ("00:00:00",),
        (" 00:00",),
        "00:00",
        ("00:00 ",),
        ("00:60",),
        ("00:00", 3),
        ("24:00",),
    ],
)
def test_activation_grid_rejects_invalid_birth_time_grids(birth_times: object) -> None:
    with pytest.raises(ValueError):
        calculation_core.calculate_activation_grid(
            **_grid_kwargs(), birth_times=birth_times, techniques=["annual_profection"]
        )


# END_BLOCK: VALIDATION


# START_BLOCK: REUSE
def test_activation_grid_reuses_target_and_timing_solver_in_request_order(monkeypatch: pytest.MonkeyPatch) -> None:
    target_context = SimpleNamespace(target_jd=123.45)
    target_calls: list[dict] = []
    natal_calls: list[dict] = []
    natal_contexts: list[object] = []
    layer_calls: list[dict] = []
    solver = object()

    def prepare_target(**kwargs):
        target_calls.append(kwargs)
        return target_context

    def prepare_natal(**kwargs):
        natal_calls.append(kwargs)
        context = SimpleNamespace(birth_time=kwargs["birth_time"])
        natal_contexts.append(context)
        return context

    def calculate_layer(**kwargs):
        layer_calls.append(kwargs)
        return SimpleNamespace(
            birth_time=kwargs["birth_time"],
            natal_context=kwargs["natal_context"],
        )

    monkeypatch.setattr(calculation_core, "prepare_target_context", prepare_target)
    monkeypatch.setattr(calculation_core, "prepare_natal_context", prepare_natal)
    monkeypatch.setattr(calculation_core, "calculate_activation_layer", calculate_layer)
    solver_factory = Mock(return_value=solver)
    monkeypatch.setattr(calculation_core, "TransitTimingSolver", solver_factory)

    result = calculation_core.calculate_activation_grid(
        **_grid_kwargs(),
        birth_times=("00:00", "03:00", "05:59"),
        techniques=["transit_to_natal"],
    )

    assert len(result) == 3
    assert len(target_calls) == 1
    assert len(natal_calls) == 3
    assert [call["birth_time"] for call in natal_calls] == ["00:00", "03:00", "05:59"]
    assert len({id(context) for context in natal_contexts}) == 3
    assert len(layer_calls) == 3
    assert [call["natal_context"] is context for call, context in zip(layer_calls, natal_contexts, strict=True)] == [True, True, True]
    assert all(call["target_context"] is target_context for call in layer_calls)
    assert all(call["timing_solver"] is solver for call in layer_calls)
    assert all(call["timing_scope"] == "convergence_eligible" for call in layer_calls)
    assert [layer.birth_time for layer in result] == ["00:00", "03:00", "05:59"]
    assert [layer.natal_context is context for layer, context in zip(result, natal_contexts, strict=True)] == [True, True, True]
    solver_factory.assert_called_once_with(target_jd=123.45)


def test_activation_grid_non_transit_technique_does_not_create_timing_solver(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(calculation_core, "prepare_target_context", lambda **_: SimpleNamespace(target_jd=1.0))
    monkeypatch.setattr(calculation_core, "prepare_natal_context", lambda **_: object())
    monkeypatch.setattr(calculation_core, "calculate_activation_layer", lambda **_: _layer())

    def unexpected_solver(**_kwargs):
        raise AssertionError("non-transit grid must not create a timing solver")

    monkeypatch.setattr(calculation_core, "TransitTimingSolver", unexpected_solver)
    result = calculation_core.calculate_activation_grid(
        **_grid_kwargs(), birth_times=("00:00", "04:00"), techniques=["annual_profection"]
    )

    assert len(result) == 2


# END_BLOCK: REUSE


# START_BLOCK: HTTP
def _grid_request(times: list[str]) -> dict:
    return {
        "birth": {
            "date": "1990-01-15",
            "times": times,
            "lat": 55.7558,
            "lon": 37.6173,
            "tz": "Europe/Moscow",
        },
        "target": {"date": "2026-07-08", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": [],
    }


@pytest.mark.parametrize(
    "times",
    [
        ["14:27"],
        ["00:00", "03:00", "05:59"],
        ["00:00", "04:00", "08:00", "12:00", "16:00", "20:00", "23:59"],
    ],
)
def test_activation_grid_endpoint_accepts_canonical_grids_and_preserves_order(monkeypatch, times):
    monkeypatch.setattr(activation_api, "calculate_activation_grid", lambda **_: tuple(_layer() for _ in times))
    response = client.post("/v1/activation-layer-grid", json=_grid_request(times))

    assert response.status_code == 200
    data = response.json()
    assert data["meta"]["sample_count"] == len(times)
    assert data["meta"]["ephemeris_artifact_id"]
    assert [sample["birth_time"] for sample in data["samples"]] == times
    assert all(sample["activation_layer"]["calculation_version"] == versions.CALCULATION_VERSION for sample in data["samples"])


def test_activation_grid_endpoint_reads_verified_identity_once(monkeypatch):
    identity = SimpleNamespace(artifact_id="swieph-test-artifact")
    identity_getter = Mock(return_value=identity)
    grid_calculator = Mock(return_value=(_layer(),))
    monkeypatch.setattr(activation_api, "get_identity", identity_getter, raising=False)
    monkeypatch.setattr(activation_api, "calculate_activation_grid", grid_calculator)

    response = client.post("/v1/activation-layer-grid", json=_grid_request(["14:27"]))

    assert response.status_code == 200
    assert response.json()["meta"]["ephemeris_artifact_id"] == "swieph-test-artifact"
    identity_getter.assert_called_once_with()
    grid_calculator.assert_called_once()


def test_activation_grid_endpoint_identity_failures_are_generic(monkeypatch):
    monkeypatch.setattr(
        activation_api,
        "get_identity",
        lambda: (_ for _ in ()).throw(RuntimeError("secret identity details")),
        raising=False,
    )

    response = client.post("/v1/activation-layer-grid", json=_grid_request(["14:27"]))

    assert response.status_code == 500
    assert response.json() == {"detail": "Activation layer grid calculation failed"}
    assert "secret identity details" not in response.text


@pytest.mark.parametrize("identity", [SimpleNamespace(artifact_id=""), SimpleNamespace()])
def test_activation_grid_endpoint_rejects_empty_or_missing_identity(monkeypatch, identity):
    monkeypatch.setattr(activation_api, "get_identity", lambda: identity, raising=False)

    response = client.post("/v1/activation-layer-grid", json=_grid_request(["14:27"]))

    assert response.status_code == 500
    assert response.json() == {"detail": "Activation layer grid calculation failed"}


def test_activation_grid_endpoint_reports_real_test_only_moshier_identity(monkeypatch):
    def reject_pinned_artifact(*_args, **_kwargs):
        raise ephemeris_runtime.EphemerisError("test-only forced artifact failure")

    monkeypatch.setattr(ephemeris_runtime, "_load_and_verify_manifest", reject_pinned_artifact)
    monkeypatch.setattr(activation_api, "calculate_activation_grid", lambda **_: (_layer(),))

    response = client.post("/v1/activation-layer-grid", json=_grid_request(["14:27"]))

    assert response.status_code == 200
    assert response.json()["meta"]["ephemeris_artifact_id"] == "moshier-only"


@pytest.mark.parametrize(
    "times",
    [[], ["00:00"] * 8, ["03:00", "00:00"], ["00:00", "00:00"], ["1:00"], ["24:00"]],
)
def test_activation_grid_endpoint_rejects_invalid_grids_with_422(times):
    response = client.post("/v1/activation-layer-grid", json=_grid_request(times))

    assert response.status_code == 422


def test_activation_grid_endpoint_returns_generic_500(monkeypatch):
    monkeypatch.setattr(
        activation_api,
        "calculate_activation_grid",
        lambda **_: (_ for _ in ()).throw(RuntimeError("secret birth data 1980-10-30")),
    )
    response = client.post("/v1/activation-layer-grid", json=_grid_request(["14:27"]))

    assert response.status_code == 500
    assert response.json() == {"detail": "Activation layer grid calculation failed"}
    assert "1980-10-30" not in response.text


# END_BLOCK: HTTP


# START_BLOCK: PARITY
def test_one_point_grid_matches_direct_convergence_scoped_calculation() -> None:
    kwargs = {
        **_grid_kwargs(),
        "birth_date": "1990-01-15",
        "birth_time": "14:30",
        "techniques": ["transit_to_natal"],
    }
    direct = calculation_core.calculate_activation_layer(
        **kwargs, timing_scope="convergence_eligible"
    )
    grid = calculation_core.calculate_activation_grid(
        **{key: value for key, value in kwargs.items() if key != "birth_time"},
        birth_times=("14:30",),
    )

    assert grid[0].model_dump(mode="json") == direct.model_dump(mode="json")


# END_BLOCK: PARITY
