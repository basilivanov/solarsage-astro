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
#   - create_app: public entrypoint function to instantiate FastAPI app
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
#   - allow_origins is restricted to policy.cors_allowed_origins
#   - CorrelationMiddleware runs before CORS
#   - debug, metrics, health_extended, and microcopy routers are mounted dev-only
# failure_policy:
#   - any import-time error must crash the process; partial boot is forbidden
# non_goals:
#   - no business logic
#   - no DB session management (lives in M-DB-SESSION)
# END_MODULE_CONTRACT: M-API-BOOT

# START_MODULE_MAP: M-API-BOOT
# public_entrypoints:
#   - create_app
#   - app
# semantic_blocks:
#   - APP_CONSTRUCTION: FastAPI() instantiation with title and version
#   - CORS_WIRING: CORSMiddleware registration with allow_origins
#   - ROUTER_MOUNT: include_router for health
# owned_tests:
#   - apps/api/tests/test_health.py
#   - apps/api/tests/test_public_surface_security.py
# END_MODULE_MAP: M-API-BOOT

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import _log, access, auth, calendar, chat, checkin, day, election, geo, health, horary, natal, payment, profile, promo, referral, synastry, telegram_webhook, today_convergence
from app.core.config import Settings, settings
from app.core.runtime_security import build_runtime_security_policy
from app.middleware.correlation import CorrelationMiddleware


def create_app(app_settings: Settings = settings) -> FastAPI:
    # START_FUNCTION_CONTRACT: F-M-API-BOOT.create_app
    # purpose: Construct the FastAPI application using the provided Settings.
    # inputs: app_settings — Settings instance.
    # returns: FastAPI — the configured application.
    # side_effects: registers CORS, mounts routers, validates canon bundle.
    # emitted_logs: none
    # error_behavior: Throws ValueError if settings are invalid.
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
    application = FastAPI(title="Astro API", version=app_settings.app_version)
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
