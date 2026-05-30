# ############################################################################
# AI_HEADER: MODULE_API_BOOT
# ROLE: FastAPI composition root — constructs app, wires CORS, mounts routers.
# DEPENDENCIES: fastapi, app.core.config, app.api.health
# GRACE_ANCHORS: [APP_CONSTRUCTION, CORS_WIRING, ROUTER_MOUNT]
# ############################################################################

# START_MODULE_CONTRACT: M-API-BOOT
# purpose: Construct the FastAPI application, wire CORS, and mount the health
#   router. This module is the single composition root for the API.
# owns:
#   - apps/api/app/main.py
#   - apps/api/app/__init__.py
#   - apps/api/app/api/__init__.py
# inputs:
#   - settings.app_version, settings.app_env, settings.app_domain (from M-CONFIG)
#   - app.api.health.router
# outputs:
#   - app: FastAPI ASGI application served by uvicorn
# dependencies:
#   - M-CONFIG
#   - app.api.health (mounts GET /api/health)
# side_effects:
#   - registers CORS middleware
#   - mounts routers
# invariants:
#   - in production, allow_origins is restricted to https://{app_domain}
#   - feature routers (day/calendar/profile/readings/auth) are NOT mounted
#     here in W-1.1 — they belong to later waves
# failure_policy:
#   - any import-time error must crash the process; partial boot is forbidden
# non_goals:
#   - no business logic
#   - no DB session management (lives in M-DB-SESSION)
#   - no telemetry wiring (deferred)
# END_MODULE_CONTRACT: M-API-BOOT

# START_MODULE_MAP: M-API-BOOT
# public_entrypoints:
#   - app
# semantic_blocks:
#   - APP_CONSTRUCTION: FastAPI() instantiation with title and version
#   - CORS_WIRING: CORSMiddleware registration with allow_origins
#   - ROUTER_MOUNT: include_router for health
# owned_tests:
#   - apps/api/tests/test_health.py
# END_MODULE_MAP: M-API-BOOT

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import auth, calendar, day, health, profile
from app.core.config import settings

# START_BLOCK: APP_CONSTRUCTION
app = FastAPI(title="Astro API", version=settings.app_version)
# END_BLOCK: APP_CONSTRUCTION

# START_BLOCK: CORS_WIRING
app.add_middleware(
    CORSMiddleware,
    allow_origins=(
        [f"https://{settings.app_domain}"]
        if settings.app_env == "production"
        else ["*"]
    ),
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)
# END_BLOCK: CORS_WIRING

# START_BLOCK: ROUTER_MOUNT
app.include_router(health.router)
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(day.router)  # W-1.3
app.include_router(calendar.router)  # W-1.4
# END_BLOCK: ROUTER_MOUNT
