
# ############################################################################
# AI_HEADER: MODULE_SOLARSAGE_APP
# ROLE: Sidecar calculation
# DEPENDENCIES: local modules
# GRACE_ANCHORS: []
# SLICE: SLICE-SIDECAR-CALCULATION
# ######################################### START_MODULE_CONTRACT
# purpose: HTTP routes for app operations
# owns:
#   - apps/solarsage/solarsage/app.py
# inputs: HTTP request, path/query params
# outputs: HTTP response / JSON body
# dependencies: local modules
# side_effects: Processes HTTP requests
# emitted_logs: n/a (pure)
# invariants:
#   - n/a
# failure_policy: log and raise
# END_MODULE_CONTRACT
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
