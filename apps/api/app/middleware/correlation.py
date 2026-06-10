# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_CORRELATION
# ROLE: Correlation ID middleware for request tracing.
# DEPENDENCIES: uuid, starlette, contextvars
# GRACE_ANCHORS: [CORRELATION_MIDDLEWARE]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-CORRELATION
# purpose: Read or mint correlation IDs for request tracing, bind log context
#   vars, and emit system.request events.
# owns:
#   - apps/api/app/middleware/correlation.py
# inputs:
#   - X-Correlation-Id header from incoming request (optional)
#   - request scope: http method, route template
# outputs:
#   - X-Correlation-Id header in response
#   - request.state.correlation_id for downstream use
#   - contextvars bound for automatic log enrichment
#   - system.request log event on completion
# dependencies:
#   - uuid (standard library)
#   - starlette.middleware.base
#   - app.core.logging (bind_log_context, clear_log_context, log_event)
# side_effects:
#   - mutates request.state
#   - adds response header
#   - writes system.request log event
# invariants:
#   - every request has a correlation_id (read or minted)
#   - correlation_id is echoed in response header
#   - log context is bound before request and cleared after
#   - system.request event is emitted after response
# failure_policy:
#   - middleware errors must not block request processing
# END_MODULE_CONTRACT: M-OBSERVABILITY-CORRELATION

from __future__ import annotations

import os
import time
import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.logging import (
    bind_log_context,
    clear_log_context,
    log_event,
)


# START_BLOCK: CORRELATION_MIDDLEWARE
class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs and bind log context.

    Reads X-Correlation-Id from request header, or mints a new UUIDv4.
    Binds contextvars for automatic log enrichment.
    Emits system.request event after response.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and inject correlation ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            Response with X-Correlation-Id header.
        """
        start_time = time.monotonic()

        # Read or mint correlation ID
        correlation_id = request.headers.get("X-Correlation-Id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Build route template (strip raw URL params)
        route_template = request.url.path
        if request.scope.get("route") and hasattr(request.scope["route"], "path"):
            route_template = request.scope["route"].path

        # Bind log context
        bind_log_context(
            correlation_id=correlation_id,
            http_route=route_template,
            http_method=request.method,
            slice="W-1.6",
            module="M-OBSERVABILITY-CORRELATION",
            block="CORRELATION_MIDDLEWARE",
            env=os.getenv("GRACE_ENV", "dev"),
        )

        # Store in request state
        request.state.correlation_id = correlation_id

        try:
            # Call next middleware/route
            response: Response = await call_next(request)

            # Echo correlation ID in response header
            response.headers["X-Correlation-Id"] = correlation_id

            # Emit system.request event
            duration_ms = (time.monotonic() - start_time) * 1000
            log_event(
                "system.request",
                level="info",
                msg=f"{request.method} {route_template} -> {response.status_code}",
                duration_ms=duration_ms,
                http={
                    "method": request.method,
                    "route": route_template,
                    "status": response.status_code,
                },
            )

            return response

        except Exception as exc:
            duration_ms = (time.monotonic() - start_time) * 1000
            log_event(
                "system.error",
                level="error",
                msg=f"Unhandled exception: {type(exc).__name__}",
                duration_ms=duration_ms,
                error={
                    "kind": type(exc).__name__,
                    "message": str(exc)[:200],
                },
                http={
                    "method": request.method,
                    "route": route_template,
                    "status": 500,
                },
            )
            raise
        finally:
            # Clean up context
            clear_log_context()
# END_BLOCK: CORRELATION_MIDDLEWARE
