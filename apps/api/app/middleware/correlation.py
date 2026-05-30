# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_CORRELATION
# ROLE: Correlation ID middleware for request tracing.
# DEPENDENCIES: uuid, starlette
# GRACE_ANCHORS: [CORRELATION_MIDDLEWARE]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-CORRELATION
# purpose: Read or mint correlation IDs for request tracing, and echo them
#   in response headers.
# owns:
#   - apps/api/app/middleware/correlation.py
# inputs:
#   - X-Correlation-Id header from incoming request (optional)
# outputs:
#   - X-Correlation-Id header in response
#   - request.state.correlation_id for downstream use
# dependencies:
#   - uuid (standard library)
#   - starlette.middleware.base
# side_effects:
#   - mutates request.state
#   - adds response header
# invariants:
#   - every request has a correlation_id (read or minted)
#   - correlation_id is echoed in response header
#   - minted IDs are valid UUIDv4
# failure_policy:
#   - middleware errors must not block request processing
# non_goals:
#   - no correlation ID propagation to external services (deferred)
#   - no correlation ID validation (accept any non-empty string)
# END_MODULE_CONTRACT: M-OBSERVABILITY-CORRELATION

import uuid

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response


# START_BLOCK: CORRELATION_MIDDLEWARE
class CorrelationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle correlation IDs.

    Reads X-Correlation-Id from request header, or mints a new UUIDv4 if absent.
    Stores correlation_id in request.state for downstream use.
    Echoes correlation_id in response X-Correlation-Id header.
    """

    async def dispatch(self, request: Request, call_next):
        """Process request and inject correlation ID.

        Args:
            request: Incoming HTTP request.
            call_next: Next middleware or route handler.

        Returns:
            Response with X-Correlation-Id header.
        """
        # Read or mint correlation ID
        correlation_id = request.headers.get("X-Correlation-Id")
        if not correlation_id:
            correlation_id = str(uuid.uuid4())

        # Store in request state
        request.state.correlation_id = correlation_id

        # Call next middleware/route
        response: Response = await call_next(request)

        # Echo correlation ID in response header
        response.headers["X-Correlation-Id"] = correlation_id

        return response
# END_BLOCK: CORRELATION_MIDDLEWARE
