# ############################################################################
# AI_HEADER: MODULE_SIDECAR_ACTIVATION_BUILDER — sidecar activation layer builder.
# ROLE: W2 contract-only builder. Returns empty activation layer with warnings.
#       W3+ will populate with real transit astronomy computations.
# ############################################################################

from __future__ import annotations

from solarsage.schemas.activation import ActivationLayer


def build_activation_layer(
    *,
    birth_date: str,
    birth_time: str,
    birth_lat: float,
    birth_lon: float,
    birth_tz: str,
    target_date: str,
    target_time: str,
    target_tz: str,
    house_system: str,
) -> ActivationLayer:
    """Build activation layer for a given birth + target context.

    W2: contract-only. Returns an empty activation layer with a warning
    that no techniques have been built yet. W3+ will implement the actual
    transit-based activation extraction with Swiss Ephemeris.
    """
    return ActivationLayer(
        calculation_version="1",
        target_date=target_date,
        target_time=target_time,
        target_tz=target_tz,
        house_system=house_system,
        activations=[],
        by_planet={},
        by_house={},
        by_lot={},
        by_angle={},
        warnings=["contract_only_no_techniques_built_yet"],
    )
