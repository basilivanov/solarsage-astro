# AI_HEADER: MODULE_SOLARSAGE_CLIENT
# wave: W-3.4
# purpose: HTTP client for SolarSage sidecar

# START_MODULE_CONTRACT: M-SOLARSAGE-CLIENT
# purpose: HTTP client for SolarSage sidecar (POST /v1/natal, POST /v1/transits).
# owns:
#   - apps/api/app/clients/solarsage_client.py
# inputs:
#   - birth_date, birth_time, birth_lat, birth_lon, birth_tz (for get_natal)
#   - target_date, target_time, target_tz (for get_transits)
# outputs:
#   - dict with planets, houses, special_points (natal)
#   - dict with planets, target_jd (transits)
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
#   - get_solarsage_client
# semantic_blocks:
#   - CLIENT_CLASS: SolarSageClient with httpx.AsyncClient
#   - SINGLETON: module-level _client instance
# owned_tests:
#   - apps/api/tests/test_solarsage_client.py
# END_MODULE_MAP: M-SOLARSAGE-CLIENT

from __future__ import annotations

import httpx

from app.core.config import settings


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

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
# END_BLOCK: CLIENT_CLASS


# START_BLOCK: SINGLETON
_client: SolarSageClient | None = None


def get_solarsage_client() -> SolarSageClient:
    """Get singleton SolarSage client."""
    global _client
    if _client is None:
        _client = SolarSageClient()
    return _client
# END_BLOCK: SINGLETON
