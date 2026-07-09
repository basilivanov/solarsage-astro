# ############################################################################
# AI_HEADER: MODULE_SIDECAR_API_ACTIVATION_LAYER — activation layer endpoint.
# ROLE: POST /v1/activation-layer — contract endpoint.
#       W2: returns an empty activation layer. W3+ will compute real activations.
# ############################################################################

from fastapi import APIRouter, HTTPException

from ..schemas.activation import ActivationLayer
from ..services.activation_builder import build_activation_layer

router = APIRouter(prefix="/v1", tags=["activation_layer"])


class ActivationLayerRequest:
    """Request shape for /v1/activation-layer."""


class BirthInfo:
    """Birth information for activation calculation."""


class TargetInfo:
    """Target date/time/timezone for activation calculation."""


from pydantic import BaseModel, Field


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


class ActivationLayerRequest(BaseModel):
    birth: BirthRequest
    target: TargetRequest
    house_system: str = Field(default="PLACIDUS", description="House system")
    techniques: list[str] = Field(default_factory=list)


class ActivationLayerMeta(BaseModel):
    calculation_version: str
    activation_layer_version: str = "al-1.0"
    house_system: str


class ActivationLayerResponse(BaseModel):
    meta: ActivationLayerMeta
    activation_layer: ActivationLayer


@router.post("/activation-layer", response_model=ActivationLayerResponse)
async def post_activation_layer(request: ActivationLayerRequest) -> ActivationLayerResponse:
    """Calculate activation layer for a given birth chart and target date.
    
    W2: contract-only. Returns empty activation layer with a warning.
    """
    try:
        layer = build_activation_layer(
            birth_date=request.birth.date,
            birth_time=request.birth.time,
            birth_lat=request.birth.lat,
            birth_lon=request.birth.lon,
            birth_tz=request.birth.tz,
            target_date=request.target.date,
            target_time=request.target.time,
            target_tz=request.target.tz,
            house_system=request.house_system,
        )

        meta = ActivationLayerMeta(
            calculation_version=layer.calculation_version,
            activation_layer_version=layer.activation_layer_version,
            house_system=layer.house_system,
        )

        return ActivationLayerResponse(meta=meta, activation_layer=layer)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Activation layer calculation failed: {str(e)}")
