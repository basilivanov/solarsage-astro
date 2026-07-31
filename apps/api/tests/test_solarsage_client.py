
# ############################################################################
# AI_HEADER: MODULE_TESTS_TEST_SOLARSAGE_CLIENT
# ROLE: Module
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-TESTS
# ######################################### START_MODULE_CONTRACT
# purpose: Tests for solarsage_client.py behavior
# owns:
#   - apps/api/tests/test_solarsage_client.py
# inputs: Endpoint params, request body
# outputs: Parsed response / typed data
# dependencies: local modules
# side_effects: Network calls to API
# emitted_logs: n/a (tests)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
# AI_HEADER
# module: M-TEST-SOLARSAGE-CLIENT
# wave: W-3.4
# purpose: SolarSage client tests

import pytest
from copy import deepcopy
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import app.clients.solarsage_client as client_module
from app.clients.solarsage_client import ActivationGridSample, SolarSageClient, SolarSageClientError
from app.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from app.schemas.activation import ActivationLayer


@pytest.mark.asyncio
async def test_get_natal():
    """SolarSage client calls POST /v1/natal."""
    client = SolarSageClient()

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "planets": [
            {
                "name": "Sun",
                "longitude": 69.5,
                "latitude": 0.0,
                "speed": 1.0,
                "sign": "Gemini",
            }
        ],
        "houses": [
            {
                "number": 1,
                "cusp": 10.0,
                "sign": "Aries",
            }
        ],
        "special_points": [],
        "house_system": "PLACIDUS",
    }
    mock_response.raise_for_status = MagicMock()

    # Mock the async post method
    mock_post = AsyncMock(return_value=mock_response)

    with patch.object(client.client, "post", mock_post):
        result = await client.get_natal(
            birth_date="1990-01-15",
            birth_time="14:30",
            birth_lat=55.7558,
            birth_lon=37.6173,
            birth_tz="Europe/Moscow",
        )

        # Check that POST was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/v1/natal"

        # Check payload
        payload = call_args[1]["json"]
        assert payload["birth_date"] == "1990-01-15"
        assert payload["birth_time"] == "14:30"
        assert payload["birth_lat"] == 55.7558
        assert payload["birth_lon"] == 37.6173
        assert payload["birth_tz"] == "Europe/Moscow"

        # Check result
        assert "planets" in result
        assert len(result["planets"]) == 1
        assert result["planets"][0]["name"] == "Sun"
        assert result["planets"][0]["latitude"] == 0.0


@pytest.mark.asyncio
async def test_get_transits():
    """SolarSage client calls POST /v1/transits."""
    client = SolarSageClient()

    # Mock httpx response
    mock_response = MagicMock()
    mock_response.json.return_value = {
        "planets": [
            {
                "name": "Sun",
                "longitude": 69.5,
                "latitude": 0.0,
                "speed": 1.0,
                "sign": "Gemini",
            }
        ],
        "target_jd": 2461190.0,
    }
    mock_response.raise_for_status = MagicMock()

    # Mock the async post method
    mock_post = AsyncMock(return_value=mock_response)

    with patch.object(client.client, "post", mock_post):
        result = await client.get_transits(
            target_date="2026-05-30",
            target_time="12:00",
            target_tz="Europe/Moscow",
        )

        # Check that POST was called
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        assert call_args[0][0] == "/v1/transits"

        # Check payload
        payload = call_args[1]["json"]
        assert payload["target_date"] == "2026-05-30"
        assert payload["target_time"] == "12:00"
        assert payload["target_tz"] == "Europe/Moscow"

        # Check result
        assert "planets" in result
        assert "targetJd" in result
        assert result["targetJd"] == 2461190.0
        assert result["planets"][0]["latitude"] == 0.0


@pytest.mark.asyncio
async def test_validation_errors():
    """SolarSageClient fails if sidecar response is invalid or missing required fields."""
    from pydantic import ValidationError
    from app.schemas.natal import SolarSageNatalResponse, SolarSageTransitsResponse

    # 1. Missing houses
    with pytest.raises(ValidationError):
        SolarSageNatalResponse.model_validate({
            "planets": [{"name": "Sun", "longitude": 69.5, "sign": "Gemini", "speed": 1.0}],
            "houses": [],
            "special_points": [],
        })

    # 2. Missing planets in transits
    with pytest.raises(ValidationError):
        SolarSageTransitsResponse.model_validate({
            "planets": [],
            "target_jd": 2461190.0,
        })


def _valid_grid_layer() -> dict:
    return ActivationLayer(
        calculation_version=CALCULATION_VERSION,
        activation_layer_version=ACTIVATION_LAYER_VERSION,
        target_date="2026-07-08",
        target_time="12:00",
        target_tz="Europe/Moscow",
        house_system="PLACIDUS",
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
    ).model_dump(mode="json")


def _valid_grid_response(times: list[str]) -> dict:
    return {
        "meta": {
            "calculation_version": CALCULATION_VERSION,
            "activation_layer_version": ACTIVATION_LAYER_VERSION,
            "sample_count": len(times),
            "ephemeris_artifact_id": "swieph-test-artifact",
        },
        "samples": [
            {"birth_time": birth_time, "activation_layer": _valid_grid_layer()}
            for birth_time in times
        ],
    }


@pytest.mark.asyncio
async def test_get_activation_layer_grid_posts_once_and_returns_ordered_typed_samples():
    client = SolarSageClient()
    times = ["00:00", "03:00", "05:59"]
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _valid_grid_response(times)
    mock_post = AsyncMock(return_value=response)

    with patch.object(client.client, "post", mock_post):
        result = await client.get_activation_layer_grid(
            birth_date="1980-10-30",
            birth_times=times,
            birth_lat=67.9394,
            birth_lon=32.8144,
            birth_tz="Europe/Moscow",
            target_date="2026-07-08",
            target_time="12:00",
            target_tz="Europe/Moscow",
            techniques=["transit_to_natal"],
        )

    mock_post.assert_called_once()
    assert mock_post.call_args.args == ("/v1/activation-layer-grid",)
    assert mock_post.call_args.kwargs["json"] == {
        "birth": {
            "date": "1980-10-30",
            "times": times,
            "lat": 67.9394,
            "lon": 32.8144,
            "tz": "Europe/Moscow",
        },
        "target": {"date": "2026-07-08", "time": "12:00", "tz": "Europe/Moscow"},
        "house_system": "PLACIDUS",
        "techniques": ["transit_to_natal"],
    }
    assert hasattr(client_module, "ActivationGridBatch")
    assert isinstance(result, client_module.ActivationGridBatch)
    assert result.calculation_version == CALCULATION_VERSION
    assert result.activation_layer_version == ACTIVATION_LAYER_VERSION
    assert result.ephemeris_artifact_id == "swieph-test-artifact"
    assert isinstance(result.samples, tuple)
    assert isinstance(result.samples[0], ActivationGridSample)
    assert all(isinstance(sample, ActivationGridSample) for sample in result.samples)
    assert [sample.birth_time for sample in result.samples] == times
    assert all(isinstance(sample.activation_layer, ActivationLayer) for sample in result.samples)
    with pytest.raises((AttributeError, TypeError)):
        result.ephemeris_artifact_id = "changed"  # type: ignore[misc]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "artifact_id",
    [None, "", " " * 128, [], True, "x" * 129, f"{' ' * 128}x"],
)
async def test_get_activation_layer_grid_rejects_invalid_ephemeris_artifact_id(artifact_id):
    client = SolarSageClient()
    payload = _valid_grid_response(["00:00"])
    payload["meta"]["ephemeris_artifact_id"] = artifact_id
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload

    with patch.object(client.client, "post", AsyncMock(return_value=response)):
        with pytest.raises(
            SolarSageClientError,
            match=r"^solarsage_client:activation_grid:ephemeris_artifact_id$",
        ):
            await client.get_activation_layer_grid(
                birth_date="1980-10-30",
                birth_times=["00:00"],
                birth_lat=67.9394,
                birth_lon=32.8144,
                birth_tz="Europe/Moscow",
                target_date="2026-07-08",
                target_time="12:00",
                target_tz="Europe/Moscow",
            )


@pytest.mark.asyncio
async def test_get_activation_layer_grid_rejects_missing_ephemeris_artifact_id() -> None:
    client = SolarSageClient()
    payload = _valid_grid_response(["00:00"])
    payload["meta"].pop("ephemeris_artifact_id")
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = payload

    with patch.object(client.client, "post", AsyncMock(return_value=response)):
        with pytest.raises(
            SolarSageClientError,
            match=r"^solarsage_client:activation_grid:ephemeris_artifact_id$",
        ):
            await client.get_activation_layer_grid(
                birth_date="1980-10-30",
                birth_times=["00:00"],
                birth_lat=67.9394,
                birth_lon=32.8144,
                birth_tz="Europe/Moscow",
                target_date="2026-07-08",
                target_time="12:00",
                target_tz="Europe/Moscow",
            )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "mutation",
    [
        lambda _data: [],
        lambda data: data.update(meta=[]),
        lambda data: data.update(samples={}),
        lambda data: data.pop("meta"),
        lambda data: data["meta"].pop("calculation_version"),
        lambda data: data["meta"].update(sample_count=99),
        lambda data: data["meta"].update(sample_count="2"),
        lambda data: data["meta"].update(sample_count=True),
        lambda data: data.pop("samples"),
        lambda data: data["meta"].pop("activation_layer_version"),
        lambda data: data["meta"].update(activation_layer_version="other"),
        lambda data: data["samples"].__setitem__(0, []),
        lambda data: data["samples"].__setitem__(1, {**data["samples"][1], "birth_time": "00:00"}),
        lambda data: data.update(samples=data["samples"] + [{"birth_time": "09:00", "activation_layer": _valid_grid_layer()}]),
        lambda data: data["meta"].update(calculation_version="other"),
        lambda data: data["samples"][0]["activation_layer"].pop("calculation_version"),
        lambda data: data["samples"][0]["activation_layer"].update(calculation_version="other"),
    ],
)
async def test_get_activation_layer_grid_rejects_malformed_response(mutation):
    client = SolarSageClient()
    payload = _valid_grid_response(["00:00", "03:00"])
    malformed = deepcopy(payload)
    mutated = mutation(malformed)
    if mutated is not None:
        malformed = mutated
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = malformed
    mock_post = AsyncMock(return_value=response)
    legacy_fallback = AsyncMock()

    with patch.object(client.client, "post", mock_post), patch.object(client, "get_activation_layer", legacy_fallback):
        with pytest.raises(SolarSageClientError, match="solarsage_client:activation_grid:"):
            await client.get_activation_layer_grid(
                birth_date="1980-10-30",
                birth_times=["00:00", "03:00"],
                birth_lat=67.9394,
                birth_lon=32.8144,
                birth_tz="Europe/Moscow",
                target_date="2026-07-08",
                target_time="12:00",
                target_tz="Europe/Moscow",
            )

    assert mock_post.call_count == 1
    assert mock_post.call_args.args == ("/v1/activation-layer-grid",)
    legacy_fallback.assert_not_awaited()


@pytest.mark.asyncio
async def test_get_activation_layer_grid_does_not_swallow_unexpected_model_errors():
    client = SolarSageClient()
    response = MagicMock()
    response.raise_for_status = MagicMock()
    response.json.return_value = _valid_grid_response(["00:00"])
    mock_post = AsyncMock(return_value=response)

    with patch.object(client.client, "post", mock_post), patch.object(
        ActivationLayer, "model_validate", side_effect=RuntimeError("unexpected model failure")
    ):
        with pytest.raises(RuntimeError, match="unexpected model failure"):
            await client.get_activation_layer_grid(
                birth_date="1980-10-30",
                birth_times=["00:00"],
                birth_lat=67.9394,
                birth_lon=32.8144,
                birth_tz="Europe/Moscow",
                target_date="2026-07-08",
                target_time="12:00",
                target_tz="Europe/Moscow",
            )


def test_activation_grid_client_source_has_no_health_or_artifact_fallback() -> None:
    source = Path(__file__).resolve().parents[1].joinpath("app/clients/solarsage_client.py").read_text(encoding="utf-8")
    assert "/health" not in source
    assert "moshier-only" not in source
