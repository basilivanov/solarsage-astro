# AI_HEADER
# module: M-SIDECAR-APP
# wave: W-3.1, W-3.2, W-3.3
# purpose: FastAPI sidecar application

from fastapi import FastAPI

from .api import health, natal, transits
from .core.config import settings

app = FastAPI(
    title="SolarSage Sidecar",
    description="HTTP sidecar for astrological calculations",
    version=settings.calculation_version,
)

# Mount routers
app.include_router(health.router)
app.include_router(natal.router)
app.include_router(transits.router)


@app.get("/")
async def root():
    """Root endpoint (redirect to /docs)."""
    return {"message": "SolarSage Sidecar", "docs": "/docs"}
