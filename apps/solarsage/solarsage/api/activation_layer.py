# ############################################################################
# AI_HEADER: MODULE_SIDECAR_API_ACTIVATION_LAYER — activation layer endpoint.
# ROLE: POST /v1/activation-layer and /v1/activation-layer-grid — internal
#       sidecar calculation endpoints preserving the existing single-layer wire.
# ############################################################################

# START_MODULE_CONTRACT: M-SIDECAR-API-ACTIVATION-LAYER
# purpose: Expose the existing single activation-layer endpoint and the internal ordered birth-time grid boundary.
# owns:
#   - apps/solarsage/solarsage/api/activation_layer.py
# inputs: Validated single birth or ordered birth-time grid, target, technique, and location requests.
# outputs: Existing single ActivationLayerResponse or internal ActivationLayerGridResponse.
# dependencies: calculation_core and sidecar activation schemas.
# side_effects: Swiss Ephemeris calculations through the core service.
# emitted_logs: none.
# invariants: single endpoint payload/versions remain unchanged; grid is sequential and internal-only.
# failure_policy: Pydantic 422 for malformed grid requests; generic 500 for unexpected grid calculation errors.
# END_MODULE_CONTRACT: M-SIDECAR-API-ACTIVATION-LAYER

# START_MODULE_MAP: M-SIDECAR-API-ACTIVATION-LAYER
# public_entrypoints:
#   - post_activation_layer
#   - post_activation_layer_grid
# semantic_blocks:
#   - SINGLE_LAYER: existing single-layer HTTP contract.
#   - ACTIVATION_GRID: ordered internal birth-time grid HTTP boundary.
# owned_tests:
#   - apps/solarsage/tests/test_activation_layer_endpoint.py
#   - apps/solarsage/tests/test_activation_grid.py
# END_MODULE_MAP: M-SIDECAR-API-ACTIVATION-LAYER

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from ..core.versions import ACTIVATION_LAYER_VERSION, CALCULATION_VERSION
from ..schemas.activation import ActivationLayer
from ..services.calculation_core import calculate_activation_grid, calculate_activation_layer, validate_birth_time_grid

router = APIRouter(prefix="/v1", tags=["activation_layer"])


class BirthRequest(BaseModel):
    date: str = Field(..., description="Birth date YYYY-MM-DD")
    time: str = Field(..., description="Birth time HH:MM")
    lat: float = Field(..., description="Birth latitude")
    lon: float = Field(..., description="Birth longitude")
    tz: str = Field(..., description="Birth timezone")


class TargetRequest(BaseModel):
    date: str = Field(..., description="Target date YYYY-MM-DD")
    time: str = Field(..., description="Target time HH:MM")
    tz: str = Field(..., description="Target timezone")


class CurrentLocationRequest(BaseModel):
    lat: float = Field(..., description="Current latitude")
    lon: float = Field(..., description="Current longitude")
    tz: str | None = Field(default=None, description="Current timezone")


class ActivationLayerRequest(BaseModel):
    birth: BirthRequest
    target: TargetRequest
    house_system: str = Field(default="PLACIDUS", description="House system")
    techniques: list[str] = Field(default_factory=list)
    current_location: CurrentLocationRequest | None = Field(default=None, description="Current location for return chart")


class ActivationLayerMeta(BaseModel):
    calculation_version: str
    activation_layer_version: str = ACTIVATION_LAYER_VERSION
    house_system: str


class ActivationLayerResponse(BaseModel):
    meta: ActivationLayerMeta
    activation_layer: ActivationLayer


class BirthGridRequest(BaseModel):
    date: str = Field(..., description="Birth date YYYY-MM-DD")
    times: list[str] = Field(..., min_length=1, max_length=7, description="Ordered birth times HH:MM")
    lat: float = Field(..., description="Birth latitude")
    lon: float = Field(..., description="Birth longitude")
    tz: str = Field(..., description="Birth timezone")

    @field_validator("times")
    @classmethod
    def validate_times(cls, value: list[str]) -> list[str]:
        validate_birth_time_grid(value)
        return value


class ActivationLayerGridRequest(BaseModel):
    birth: BirthGridRequest
    target: TargetRequest
    house_system: str = Field(default="PLACIDUS", description="House system")
    techniques: list[str] = Field(default_factory=list)
    current_location: CurrentLocationRequest | None = Field(default=None, description="Current location for return chart")


class ActivationLayerGridMeta(BaseModel):
    calculation_version: str
    activation_layer_version: str = ACTIVATION_LAYER_VERSION
    sample_count: int


class ActivationGridSample(BaseModel):
    birth_time: str
    activation_layer: ActivationLayer


class ActivationLayerGridResponse(BaseModel):
    meta: ActivationLayerGridMeta
    samples: list[ActivationGridSample]


# START_BLOCK: SINGLE_LAYER
@router.post("/activation-layer", response_model=ActivationLayerResponse)
async def post_activation_layer(request: ActivationLayerRequest) -> ActivationLayerResponse:
    """Calculate activation layer for a given birth chart and target date.

    W3.4: solar_return and lunar_return support with optional current_location
    for return chart location.
    """
    try:
        layer = calculate_activation_layer(
            birth_date=request.birth.date,
            birth_time=request.birth.time,
            birth_lat=request.birth.lat,
            birth_lon=request.birth.lon,
            birth_tz=request.birth.tz,
            target_date=request.target.date,
            target_time=request.target.time,
            target_tz=request.target.tz,
            house_system=request.house_system,
            techniques=list(request.techniques) if request.techniques else None,
            current_location=request.current_location.model_dump() if request.current_location else None,
        )

        meta = ActivationLayerMeta(
            calculation_version=layer.calculation_version,
            activation_layer_version=layer.activation_layer_version,
            house_system=layer.house_system,
        )

        return ActivationLayerResponse(meta=meta, activation_layer=layer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activation layer calculation failed: {str(e)}")
# END_BLOCK: SINGLE_LAYER


# START_BLOCK: ACTIVATION_GRID
@router.post("/activation-layer-grid", response_model=ActivationLayerGridResponse)
async def post_activation_layer_grid(request: ActivationLayerGridRequest) -> ActivationLayerGridResponse:
    # START_FUNCTION_CONTRACT: F-M-SIDECAR-API-ACTIVATION-LAYER.post_activation_layer_grid
    # purpose: Accept an internal ordered birth-time grid and return typed activation samples.
    # inputs: validated ActivationLayerGridRequest with one to seven minute controls.
    # returns: ActivationLayerGridResponse preserving sample order and versions.
    # side_effects: one sequential core grid calculation request.
    # emitted_logs: none.
    # error_behavior: Pydantic rejects invalid grids with 422; calculation failures return generic 500.
    # END_FUNCTION_CONTRACT: F-M-SIDECAR-API-ACTIVATION-LAYER.post_activation_layer_grid
    """Calculate ordered birth-time samples with one shared target workspace."""
    try:
        layers = calculate_activation_grid(
            birth_date=request.birth.date,
            birth_times=request.birth.times,
            birth_lat=request.birth.lat,
            birth_lon=request.birth.lon,
            birth_tz=request.birth.tz,
            target_date=request.target.date,
            target_time=request.target.time,
            target_tz=request.target.tz,
            house_system=request.house_system,
            techniques=list(request.techniques) if request.techniques else None,
            current_location=request.current_location.model_dump() if request.current_location else None,
        )
        if len(layers) != len(request.birth.times):
            raise ValueError("activation grid sample count mismatch")
        versions = {(layer.calculation_version, layer.activation_layer_version) for layer in layers}
        if versions != {(CALCULATION_VERSION, ACTIVATION_LAYER_VERSION)}:
            raise ValueError("activation grid version mismatch")
        calculation_version, activation_layer_version = next(iter(versions))
        return ActivationLayerGridResponse(
            meta=ActivationLayerGridMeta(
                calculation_version=calculation_version,
                activation_layer_version=activation_layer_version,
                sample_count=len(layers),
            ),
            samples=[
                ActivationGridSample(birth_time=birth_time, activation_layer=layer)
                for birth_time, layer in zip(request.birth.times, layers, strict=True)
            ],
        )
    except Exception:
        raise HTTPException(status_code=500, detail="Activation layer grid calculation failed") from None
# END_BLOCK: ACTIVATION_GRID
