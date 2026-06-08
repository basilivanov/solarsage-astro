# ############################################################################
# AI_HEADER: MODULE_API_BOOT
# ROLE: FastAPI composition root — constructs app, wires CORS, mounts routers.
# DEPENDENCIES: fastapi, app.core.config, app.api.health
# GRACE_ANCHORS: [APP_CONSTRUCTION, CORS_WIRING, MIDDLEWARE_MOUNT, ROUTER_MOUNT]
# WAVE: W-1.1, W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-API-BOOT
# purpose: Construct the FastAPI application, wire CORS, mount middleware,
#   and mount routers. This module is the single composition root for the API.
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
#   - M-OBSERVABILITY-CORRELATION (W-1.6)
#   - M-OBSERVABILITY-LOGGING (W-1.6)
#   - app.api.health (mounts GET /api/health)
# side_effects:
#   - registers CORS middleware
#   - registers CorrelationMiddleware (W-1.6)
#   - initializes structured logging (W-1.6)
#   - mounts routers
# invariants:
#   - in production, allow_origins is restricted to https://{app_domain}
#   - CorrelationMiddleware runs before CORS
# failure_policy:
#   - any import-time error must crash the process; partial boot is forbidden
# non_goals:
#   - no business logic
#   - no DB session management (lives in M-DB-SESSION)
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

from app.api import _log, auth, calendar, chat, checkin, day, debug, geo, health, health_extended, horary, metrics, microcopy, natal, payment, profile, referral
from app.core.config import settings
from app.core.logging import logger
from app.middleware.correlation import CorrelationMiddleware

# START_BLOCK: APP_CONSTRUCTION
app = FastAPI(title="Astro API", version=settings.app_version)
# END_BLOCK: APP_CONSTRUCTION

# START_BLOCK: MIDDLEWARE_MOUNT
# W-1.6: Correlation middleware (must run before CORS)
app.add_middleware(CorrelationMiddleware)
# END_BLOCK: MIDDLEWARE_MOUNT

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
app.include_router(health_extended.router)  # W-2.7 extended health check
app.include_router(metrics.router)  # W-2.7 production metrics
app.include_router(debug.router)  # Debug endpoint for troubleshooting
app.include_router(auth.router)
app.include_router(profile.router)
app.include_router(day.router)  # W-1.3
app.include_router(calendar.router)  # W-1.4
app.include_router(referral.router)  # W-ACCESS.2
app.include_router(_log.router)  # W-1.7
app.include_router(microcopy.router)  # W-9.2
app.include_router(payment.router)  # W-6.1
app.include_router(natal.router)  # W-7.2
app.include_router(checkin.router)  # W-8.1
app.include_router(chat.router)  # W-CHAT-1
app.include_router(geo.router)  # GeoNames city autocomplete
app.include_router(horary.router)  # Horary questions (W-HORARY)
# END_BLOCK: ROUTER_MOUNT
