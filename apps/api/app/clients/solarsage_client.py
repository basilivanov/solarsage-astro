# AI_HEADER: MODULE_SOLARSAGE_CLIENT
# wave: W-3.4
# purpose: HTTP client for SolarSage sidecar

# START_MODULE_CONTRACT: M-SOLARSAGE-CLIENT
# purpose: HTTP client for SolarSage sidecar single-layer and birth-time-grid endpoints.
# owns:
#   - apps/api/app/clients/solarsage_client.py
# inputs:
#   - birth_date, birth_time, birth_lat, birth_lon, birth_tz (for get_natal)
#   - target_date, target_time, target_tz (for get_transits)
# outputs:
#   - dict with planets, houses, special_points (natal)
#   - dict with planets, target_jd (transits)
#   - immutable ActivationGridSample records (activation grid)
# dependencies:
#   - M-CONFIG (settings.solarsage_url)
#   - httpx (AsyncClient)
# side_effects:
#   - HTTP POST to sidecar
# invariants:
#   - singleton instance via get_solarsage_client()
#   - timeout 30s
# failure_policy:
#   - httpx.HTTPStatusError on non-2xx response
#   - httpx.TimeoutException on timeout
# non_goals:
#   - no retry logic (W-3.4)
#   - no caching (W-3.4)
# END_MODULE_CONTRACT: M-SOLARSAGE-CLIENT

# START_MODULE_MAP: M-SOLARSAGE-CLIENT
# public_entrypoints:
#   - SolarSageClient.get_natal
#   - SolarSageClient.get_transits
#   - SolarSageClient.get_activation_layer_grid
#   - ActivationGridSample
#   - SolarSageClientError
#   - get_solarsage_client
# semantic_blocks:
#   - CLIENT_CLASS: SolarSageClient with httpx.AsyncClient
#   - ACTIVATION_GRID: typed one-request grid transport and fail-closed response validation
#   - SINGLETON: module-level _client instance
# owned_tests:
#   - apps/api/tests/test_solarsage_client.py
# END_MODULE_MAP: M-SOLARSAGE-CLIENT

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

import httpx
from pydantic import ValidationError

from app.core.config import settings
from app.core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from app.schemas.activation import ActivationLayer


class SolarSageClientError(ValueError):
    """Raised when an internal sidecar activation-grid response is malformed."""


@dataclass(frozen=True)
class ActivationGridSample:
    """Typed ordered sample returned by the internal activation-grid endpoint."""

    birth_time: str
    activation_layer: ActivationLayer


def _grid_fail(reason: str) -> None:
    raise SolarSageClientError(f"solarsage_client:activation_grid:{reason}")


# START_BLOCK: CLIENT_CLASS
class SolarSageClient:
    """HTTP client for SolarSage sidecar."""

    def __init__(self):
        self.base_url = settings.solarsage_url
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def get_natal(
        self,
        birth_date: str,
        birth_time: str,
        birth_lat: float,
        birth_lon: float,
        birth_tz: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_natal
        # purpose: Get natal chart from SolarSage sidecar.
        # inputs: birth_date (str YYYY-MM-DD), birth_time (str HH:MM), birth_lat, birth_lon, birth_tz
        # returns: validated dict from SolarSageNatalResponse
        # side_effects: HTTP POST to sidecar
        # emitted_logs: sidecar.called, natal.sidecar_failed
        # error_behavior: raises httpx.HTTPStatusError on non-2xx, httpx.TimeoutException on timeout
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_natal
        """
        Get natal chart from sidecar.

        Args:
            birth_date: ISO date string (YYYY-MM-DD)
            birth_time: Time string (HH:MM)
            birth_lat: Birth latitude
            birth_lon: Birth longitude
            birth_tz: Birth timezone (IANA)

        Returns:
            Validated dict from SolarSageNatalResponse.
            All fields are guaranteed to match the Pydantic schema;
            unknown fields from sidecar are stripped; defaults are filled.

        Raises:
            httpx.HTTPStatusError: on non-2xx response
            httpx.TimeoutException: on timeout
        """
        response = await self.client.post(
            "/v1/natal",
            json={
                "birth_date": birth_date,
                "birth_time": birth_time,
                "birth_lat": birth_lat,
                "birth_lon": birth_lon,
                "birth_tz": birth_tz,
            },
        )
        response.raise_for_status()
        data = response.json()

        # W-NATAL-FULL: Validate and return sanitized model output.
        # Returns validated.model_dump(by_alias=True) instead of raw dict so that:
        #   1. Unknown fields from sidecar are stripped
        #   2. Default values are filled for missing fields
        #   3. Data flowing through the system is guaranteed to match the schema
        from app.schemas.natal import SolarSageNatalResponse
        validated = SolarSageNatalResponse.model_validate(data)
        return validated.model_dump(by_alias=True)

    async def get_transits(
        self,
        target_date: str,
        target_time: str,
        target_tz: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_transits
        # purpose: Get transit planets from SolarSage sidecar.
        # inputs: target_date (str YYYY-MM-DD), target_time (str HH:MM), target_tz (str IANA)
        # returns: validated dict from SolarSageTransitsResponse
        # side_effects: HTTP POST to sidecar
        # emitted_logs: sidecar.called, natal.sidecar_failed
        # error_behavior: raises httpx.HTTPStatusError on non-2xx, httpx.TimeoutException on timeout
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_transits
        """
        Get transit planets from sidecar.

        Args:
            target_date: ISO date string (YYYY-MM-DD)
            target_time: Time string (HH:MM)
            target_tz: Target timezone (IANA)

        Returns:
            Validated dict from SolarSageTransitsResponse.
            Unknown fields are stripped; defaults are filled.

        Raises:
            httpx.HTTPStatusError: on non-2xx response
            httpx.TimeoutException: on timeout
        """
        response = await self.client.post(
            "/v1/transits",
            json={
                "target_date": target_date,
                "target_time": target_time,
                "target_tz": target_tz,
            },
        )
        response.raise_for_status()
        data = response.json()

        # W-NATAL-FULL: Validate and return sanitized model output.
        from app.schemas.natal import SolarSageTransitsResponse
        validated = SolarSageTransitsResponse.model_validate(data)
        return validated.model_dump(by_alias=True)

    async def get_lunar_window(
        self,
        from_date: str,
        to_date: str,
    ) -> dict:
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_lunar_window
        # purpose: Get lunar window details from SolarSage sidecar.
        # inputs: from_date (str YYYY-MM-DD), to_date (str YYYY-MM-DD)
        # returns: dict with days list
        # side_effects: HTTP POST to sidecar /v1/lunar-window
        # error_behavior: raises httpx.HTTPStatusError on non-2xx, httpx.TimeoutException on timeout
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_lunar_window
        response = await self.client.post(
            "/v1/lunar-window",
            json={
                "from_date": from_date,
                "to_date": to_date,
            },
        )
        response.raise_for_status()
        return response.json()

    async def close(self):
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.close
        # purpose: Close the underlying HTTP client connection.
        # inputs: self
        # returns: None
        # side_effects: closes httpx.AsyncClient connection pool
        # emitted_logs: none
        # error_behavior: ignores errors during close
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.close
        """Close HTTP client."""
        await self.client.aclose()
    async def get_activation_layer(
        self,
        birth_date: str,
        birth_time: str,
        birth_lat: float,
        birth_lon: float,
        birth_tz: str,
        target_date: str,
        target_time: str,
        target_tz: str,
        house_system: str = "PLACIDUS",
        techniques: list[str] | None = None,
        current_location: dict | None = None,
    ) -> dict:
        """Get activation layer from sidecar /v1/activation-layer."""
        body = {
            "birth": {
                "date": birth_date,
                "time": birth_time,
                "lat": birth_lat,
                "lon": birth_lon,
                "tz": birth_tz,
            },
            "target": {
                "date": target_date,
                "time": target_time,
                "tz": target_tz,
            },
            "house_system": house_system,
            "techniques": techniques or [],
        }
        if current_location:
            body["current_location"] = current_location
        response = await self.client.post("/v1/activation-layer", json=body)
        response.raise_for_status()
        data = response.json()
        layer = data.get("activation_layer", data)
        return layer

    async def get_activation_layer_grid(
        self,
        birth_date: str,
        birth_times: Sequence[str],
        birth_lat: float,
        birth_lon: float,
        birth_tz: str,
        target_date: str,
        target_time: str,
        target_tz: str,
        house_system: str = "PLACIDUS",
        techniques: list[str] | None = None,
        current_location: dict | None = None,
    ) -> tuple[ActivationGridSample, ...]:
        # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_activation_layer_grid
        # purpose: Request and validate one ordered birth-time activation grid.
        # inputs: birth date/times, target moment, house system, techniques, and optional current location.
        # returns: Frozen typed samples in the exact requested birth-time order.
        # side_effects: one HTTP POST to /v1/activation-layer-grid.
        # emitted_logs: none.
        # error_behavior: raises SolarSageClientError for malformed response; HTTP errors preserve httpx behavior.
        # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_activation_layer_grid
        expected_times = tuple(birth_times)
        body = {
            "birth": {
                "date": birth_date,
                "times": list(expected_times),
                "lat": birth_lat,
                "lon": birth_lon,
                "tz": birth_tz,
            },
            "target": {
                "date": target_date,
                "time": target_time,
                "tz": target_tz,
            },
            "house_system": house_system,
            "techniques": techniques or [],
        }
        if current_location:
            body["current_location"] = current_location
        response = await self.client.post("/v1/activation-layer-grid", json=body)
        response.raise_for_status()
        data = response.json()
        if not isinstance(data, Mapping):
            _grid_fail("response_mapping")

        meta = data.get("meta")
        samples = data.get("samples")
        if not isinstance(meta, Mapping):
            _grid_fail("meta_mapping")
        if not isinstance(samples, Sequence) or isinstance(samples, (str, bytes)):
            _grid_fail("samples_sequence")
        required_meta = ("calculation_version", "activation_layer_version", "sample_count")
        if any(key not in meta for key in required_meta):
            _grid_fail("meta_fields")
        sample_count = meta["sample_count"]
        if isinstance(sample_count, bool) or not isinstance(sample_count, int):
            _grid_fail("sample_count")
        if sample_count != len(expected_times) or sample_count != len(samples):
            _grid_fail("sample_count")
        if meta["calculation_version"] != CALCULATION_VERSION:
            _grid_fail("calculation_version")
        if meta["activation_layer_version"] != ACTIVATION_LAYER_VERSION:
            _grid_fail("activation_layer_version")

        validated: list[ActivationGridSample] = []
        for expected_time, raw_sample in zip(expected_times, samples, strict=True):
            if not isinstance(raw_sample, Mapping):
                _grid_fail("sample_mapping")
            if raw_sample.get("birth_time") != expected_time:
                _grid_fail("sample_order")
            raw_layer = raw_sample.get("activation_layer")
            try:
                layer = ActivationLayer.model_validate(raw_layer)
            except ValidationError as exc:
                raise SolarSageClientError("solarsage_client:activation_grid:invalid_layer") from exc
            if (
                layer.calculation_version != CALCULATION_VERSION
                or layer.activation_layer_version != ACTIVATION_LAYER_VERSION
                or layer.calculation_version != meta["calculation_version"]
                or layer.activation_layer_version != meta["activation_layer_version"]
            ):
                _grid_fail("version_disagreement")
            validated.append(ActivationGridSample(birth_time=expected_time, activation_layer=layer))
        return tuple(validated)

# END_BLOCK: CLIENT_CLASS


# START_BLOCK: SINGLETON
_client: SolarSageClient | None = None


def get_solarsage_client() -> SolarSageClient:
    # START_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_solarsage_client
    # purpose: Get or create singleton SolarSage HTTP client.
    # inputs: none (module-level _client global)
    # returns: SolarSageClient singleton
    # side_effects: creates SolarSageClient on first call (lazy init)
    # emitted_logs: none
    # error_behavior: never raises
    # END_FUNCTION_CONTRACT: F-M-SOLARSAGE-CLIENT.get_solarsage_client
    """Get singleton SolarSage client."""
    global _client
    # The underlying httpx.AsyncClient is bound to the event loop of its
    # creator. In test suites each test may run its own loop; reusing a
    # client across loops fails with "Event loop is closed", so the
    # singleton is per-loop (one client in production, fresh per test loop).
    import asyncio
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
    if _client is None or getattr(_client, "_bound_loop", None) is not loop:
        client = SolarSageClient()
        client._bound_loop = loop  # type: ignore[attr-defined]
        _client = client
    return _client
# END_BLOCK: SINGLETON
