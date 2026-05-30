# ############################################################################
# AI_HEADER: MODULE_API_LOG_INTAKE
# ROLE: HTTP surface for POST /api/_log — accepts frontend log batches.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.log_intake, app.core.dependencies
# GRACE_ANCHORS: [ROUTE_LOG_INTAKE]
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-API-LOG-INTAKE
# purpose: Accept batches of log envelopes from frontend, validate, redact PII,
#   and forward to backend stdout for centralized observability.
# owns:
#   - apps/api/app/api/_log.py
# inputs:
#   - POST /api/_log body: LogBatch { envelopes: LogEnvelope[] }
#   - session cookie (auth required)
# outputs:
#   - {"accepted": int, "rejected": int}
# dependencies:
#   - M-LOG-INTAKE-SERVICE (process_batch)
#   - M-AUTH-TG.dependencies (require_session)
#   - M-DB-SESSION (get_session)
# side_effects:
#   - writes redacted logs to stdout via backend logger
# invariants:
#   - auth required (session cookie)
#   - validates envelope structure per §8.2
#   - redacts PII before forwarding
# failure_policy:
#   - invalid auth -> 401
#   - service error -> 500
# non_goals:
#   - no rate limiting (deferred to W-RATELIMIT)
# END_MODULE_CONTRACT: M-API-LOG-INTAKE

# START_MODULE_MAP: M-API-LOG-INTAKE
# public_entrypoints:
#   - router
# semantic_blocks:
#   - ROUTE_LOG_INTAKE: POST /api/_log handler
# owned_tests:
#   - apps/api/tests/test_log_intake.py
# END_MODULE_MAP: M-API-LOG-INTAKE

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session
from app.core.logging import logger
from app.db.models import User
from app.db.session import get_session
from app.services.log_intake import LogIntakeService

router = APIRouter()


# START_BLOCK: ROUTE_LOG_INTAKE
class LogEnvelope(BaseModel):
    """Log envelope from frontend."""

    timestamp: str
    level: str
    message: str
    correlation_id: str | None = None
    extra: dict[str, Any] | None = None


class LogBatch(BaseModel):
    """Batch of log envelopes."""

    envelopes: list[LogEnvelope]


@router.post("/api/_log")
async def intake_logs(
    batch: LogBatch,
    db: AsyncSession = Depends(get_session),
    current_user: User = Depends(require_session),
) -> dict[str, int]:
    """
    Accept log batch from frontend.

    W-1.7: Validates envelopes, redacts PII, forwards to stdout.

    Args:
        batch: Batch of log envelopes from frontend
        db: Database session
        current_user: Authenticated user (from session cookie)

    Returns:
        {"accepted": count, "rejected": count}

    Raises:
        HTTPException: 401 if not authenticated, 500 on service error
    """
    service = LogIntakeService(db)

    try:
        # Process batch
        result = await service.process_batch(
            user_id=current_user.id,
            envelopes=[e.model_dump() for e in batch.envelopes],
        )

        return {
            "accepted": result["accepted"],
            "rejected": result["rejected"],
        }

    except Exception as e:
        logger.error(f"Log intake failed: {e}", extra={"user_id": str(current_user.id)})
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log intake failed",
        ) from e


# END_BLOCK: ROUTE_LOG_INTAKE
