
# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_APP
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ############################################################################

# START_MODULE_CONTRACT
# purpose: Sidecar calculation — apps/solarsage/solarsage/app.py
# owns:
#   - apps/solarsage/solarsage/app.py
# inputs: varies
# outputs: varies
# dependencies: local modules
# side_effects: varies
# emitted_logs: n/a
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT

# START_MODULE_MAP
# mapping:
#   - function: main
#     contract: main entry point
# END_MODULE_MAP

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
