# ############################################################################
# AI_HEADER: MODULE_API_BOOT
# ROLE: FastAPI composition root — constructs app, wires CORS, cache-control and correlation middleware, mounts routers, prewarms DB.
# DEPENDENCIES: fastapi, starlette.middleware, sqlalchemy, app.core.config, app.db.session, app.api.health
# GRACE_ANCHORS: [APP_CONSTRUCTION, CORS_WIRING, MIDDLEWARE_MOUNT, CACHE_CONTROL_MIDDLEWARE, ROUTER_MOUNT, STARTUP_PREWARM]
# WAVE: W-1.1, W-1.6, W-CACHE-DELIVERY-HARDENING, W-WHITE-SCREEN-RESILIENCE
# ############################################################################

# START_MODULE_CONTRACT: M-API-BOOT
# purpose: Construct the FastAPI application, wire CORS and response middleware,
#   mount routers, and warm the database pool during startup. This module is
#   the single composition root for the API.
# owns:
#   - apps/api/app/main.py
#   - apps/api/app/__init__.py
#   - apps/api/app/api/__init__.py
# inputs:
#   - settings.app_version, settings.app_env, settings.app_domain (from M-CONFIG)
#   - app.api.health.router
# outputs:
#   - create_app: public entrypoint function to instantiate FastAPI app
#   - app: FastAPI ASGI application served by uvicorn
#   - prewarm_database_pool: startup hook that establishes and verifies a DB connection
#   - Cache-Control: no-store on every HTTP response
# dependencies:
#   - M-CONFIG
#   - M-DB-SESSION (shared async engine backed by asyncpg in deployed environments)
#   - M-OBSERVABILITY-CORRELATION (W-1.6)
#   - M-OBSERVABILITY-LOGGING (W-1.6)
#   - app.api.health (mounts GET /api/health)
# side_effects:
#   - registers CORS middleware
#   - registers CorrelationMiddleware (W-1.6)
#   - registers NoStoreMiddleware for cache hygiene
#   - initializes structured logging (W-1.6)
#   - mounts routers
#   - opens one DB connection at startup and executes SELECT 1
# invariants:
#   - allow_origins is restricted to policy.cors_allowed_origins
#   - CorrelationMiddleware runs before CORS
#   - every HTTP response carries Cache-Control: no-store
#   - debug, metrics, health_extended, and microcopy routers are mounted dev-only
#   - startup prewarm emits exactly api.prewarm_ok or api.prewarm_failed
#   - startup prewarm is fail-open; a DB failure never prevents the API from starting
# failure_policy:
#   - any import-time error must crash the process; partial boot is forbidden
#   - startup prewarm failures are logged and fall back to lazy connection
# non_goals:
#   - no business logic
#   - no DB session management (lives in M-DB-SESSION)
# END_MODULE_CONTRACT: M-API-BOOT

# START_MODULE_MAP: M-API-BOOT
# public_entrypoints:
#   - create_app
#   - app
#   - NoStoreMiddleware
#   - prewarm_database_pool
# semantic_blocks:
#   - STARTUP_PREWARM: lifespan hook warming the shared async engine with SELECT 1
#   - APP_CONSTRUCTION: FastAPI() instantiation with title and version
#   - CORS_WIRING: CORSMiddleware registration with allow_origins
#   - CACHE_CONTROL_MIDDLEWARE: Cache-Control: no-store response adapter
#   - CACHE_CONTROL_MOUNT: middleware registration
#   - ROUTER_MOUNT: include_router for health
# owned_tests:
#   - apps/api/tests/test_api_prewarm.py
#   - apps/api/tests/test_health.py
#   - apps/api/tests/test_public_surface_security.py
# END_MODULE_MAP: M-API-BOOT

import asyncio
import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.api import _log, access, auth, calendar, chat, checkin, day, election, geo, health, horary, natal, payment, profile, promo, referral, synastry, telegram_webhook, today_convergence
from app.core.config import Settings, settings
from app.core.logging import log_block, log_event
from app.core.runtime_security import build_runtime_security_policy
from app.db.session import engine
from app.middleware.correlation import CorrelationMiddleware


# START_BLOCK: CACHE_CONTROL_MIDDLEWARE
class NoStoreMiddleware(BaseHTTPMiddleware):
    """Disable HTTP caching for every API response."""

    # START_FUNCTION_CONTRACT: F-M-API-BOOT.NoStoreMiddleware.dispatch
    # purpose: Add Cache-Control: no-store to the downstream response.
    # inputs: request — incoming Starlette request; call_next — downstream ASGI callable.
    # returns: downstream Response with Cache-Control: no-store.
    # side_effects: mutates response headers.
    # emitted_logs: none.
    # error_behavior: propagates downstream exceptions unchanged.
    # END_FUNCTION_CONTRACT: F-M-API-BOOT.NoStoreMiddleware.dispatch
    async def dispatch(self, request: Request, call_next) -> Response:
        response: Response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response
# END_BLOCK: CACHE_CONTROL_MIDDLEWARE


# START_BLOCK: STARTUP_PREWARM
PREWARM_TIMEOUT_SECONDS = 10.0


async def _run_database_prewarm() -> None:
    # The shared SQLAlchemy async engine is backed by asyncpg in deployed
    # environments. Checking out a connection creates the first physical
    # asyncpg connection; SELECT 1 verifies it before uvicorn accepts traffic.
    async with engine.connect() as connection:
        await connection.execute(text("SELECT 1"))


async def prewarm_database_pool() -> None:
    # START_FUNCTION_CONTRACT: F-M-API-BOOT.prewarm_database_pool
    # purpose: Establish and verify one connection from the shared async DB
    #   pool during startup, so the first auth request does not pay the
    #   asyncpg/TCP handshake cost.
    # inputs: none (uses the shared engine from M-DB-SESSION)
    # returns: None
    # side_effects: opens one DB connection, executes SELECT 1, emits one event.
    # emitted_logs: api.prewarm_ok, api.prewarm_failed
    # error_behavior: never raises; failures are logged and startup continues
    #   with the existing lazy-connect behavior.
    # END_FUNCTION_CONTRACT: F-M-API-BOOT.prewarm_database_pool
    started_at = time.perf_counter()
    with log_block(
        slice="W-WHITE-SCREEN-RESILIENCE",
        module="M-API-BOOT",
        block="STARTUP_PREWARM",
    ):
        try:
            await asyncio.wait_for(
                _run_database_prewarm(),
                timeout=PREWARM_TIMEOUT_SECONDS,
            )
        except Exception as exc:
            log_event(
                "api.prewarm_failed",
                level="error",
                msg="Database prewarm failed; starting with lazy connect",
                payload={"error_code": type(exc).__name__},
            )
            return

        log_event(
            "api.prewarm_ok",
            msg="Database prewarm completed",
            payload={
                "duration_ms": round(
                    (time.perf_counter() - started_at) * 1000,
                    3,
                )
            },
        )


@asynccontextmanager
async def lifespan(_application: FastAPI) -> AsyncIterator[None]:
    # C1: warm the asyncpg-backed pool next to the import-time canon
    # validation. Fail-open by design: a DB outage must not prevent the API
    # from booting and serving non-DB routes.
    await prewarm_database_pool()
    yield
# END_BLOCK: STARTUP_PREWARM


def create_app(app_settings: Settings = settings) -> FastAPI:
    # START_FUNCTION_CONTRACT: F-M-API-BOOT.create_app
    # purpose: Construct the FastAPI application using the provided Settings.
    # inputs: app_settings — Settings instance.
    # returns: FastAPI — the configured application.
    # side_effects: registers CORS, mounts routers, validates canon bundle,
    #   and registers the startup DB prewarm lifespan.
    # emitted_logs: api.prewarm_ok or api.prewarm_failed at startup
    # error_behavior: Throws ValueError if settings are invalid. Startup
    #   prewarm failures are logged and do not abort boot.
    # END_FUNCTION_CONTRACT: F-M-API-BOOT.create_app

    # W1: Validate canon bundle at startup — missing/invalid canon must fail fast in dev/test
    from app.services.canon_service import validate_canon_bundle
    validate_canon_bundle()

    # W-PROD-ERROR-LOOP: Initialize Bugsink error tracking (no-op when ERROR_TRACKING_DSN is empty)
    import os
    from app.services.error_tracking import init_error_tracking
    init_error_tracking(
        os.environ.get("ERROR_TRACKING_DSN", ""),
        os.environ.get("RELEASE_SHA", ""),
    )

    policy = build_runtime_security_policy(app_settings)

    # START_BLOCK: APP_CONSTRUCTION
    application = FastAPI(
        title="Astro API",
        version=app_settings.app_version,
        lifespan=lifespan,
    )
    # END_BLOCK: APP_CONSTRUCTION

    # START_BLOCK: MIDDLEWARE_MOUNT
    # W-1.6: Correlation middleware (must run before CORS)
    application.add_middleware(CorrelationMiddleware)
    # END_BLOCK: MIDDLEWARE_MOUNT

    # START_BLOCK: CORS_WIRING
    application.add_middleware(
        CORSMiddleware,
        allow_origins=list(policy.cors_allowed_origins),
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )
    # END_BLOCK: CORS_WIRING

    # START_BLOCK: CACHE_CONTROL_MOUNT
    # Register last so this response wrapper also covers CORS preflight replies.
    application.add_middleware(NoStoreMiddleware)
    # END_BLOCK: CACHE_CONTROL_MOUNT

    # START_BLOCK: ROUTER_MOUNT
    application.include_router(health.router)

    # Mount internal routes only if enabled in policy
    if policy.internal_routes_enabled:
        # Import internal routers inline to prevent import-time leaks
        from app.api import debug, health_extended, metrics, microcopy
        application.include_router(health_extended.router)  # W-2.7 extended health check
        application.include_router(metrics.router)  # W-2.7 production metrics
        application.include_router(debug.router)  # Debug endpoint for troubleshooting
        application.include_router(microcopy.router)  # W-9.2

    application.include_router(auth.router)
    application.include_router(profile.router)
    application.include_router(access.router)
    application.include_router(today_convergence.router)  # W3 snapshot impressions
    application.include_router(day.router)  # W-1.3
    from app.api import today_sphere_page
    application.include_router(today_sphere_page.router)  # P4-D3C static sphere page
    application.include_router(calendar.router)  # W-1.4
    from app.api import readings
    application.include_router(readings.router)  # P4-D3A published day history
    application.include_router(referral.router)  # W-ACCESS.2
    application.include_router(telegram_webhook.router)  # Telegram /start webhook
    application.include_router(_log.router)  # W-1.7
    application.include_router(payment.router)  # W-6.1
    application.include_router(natal.router)  # W-7.2
    application.include_router(checkin.router)  # W-8.1
    application.include_router(chat.router)  # W-CHAT-1
    application.include_router(geo.router)  # GeoNames city autocomplete
    application.include_router(horary.router)  # Horary questions (W-HORARY)
    application.include_router(election.router)  # Election astrology searches
    application.include_router(promo.router)  # Named promo campaign endpoints
    application.include_router(synastry.router)  # Synastry compatibility reports
    # END_BLOCK: ROUTER_MOUNT

    return application


app = create_app()
