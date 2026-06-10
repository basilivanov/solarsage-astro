# ############################################################################
# AI_HEADER: MODULE_API_LOG_INTAKE
# ROLE: HTTP surface for POST /api/_log — accepts frontend log batches.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.log_intake, app.core.dependencies
# GRACE_ANCHORS: [ROUTE_LOG_INTAKE]
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-API-LOG-INTAKE
# purpose: Accept batches of canonical log envelopes from frontend, validate,
#   redact PII, and forward to backend stdout via log_event.
# owns:
#   - apps/api/app/api/_log.py
# inputs:
#   - POST /api/_log body: LogBatch { envelopes: CanonEnvelope[] }
#   - session cookie (optional auth)
# outputs:
#   - {"accepted": int, "rejected": int}
# dependencies:
#   - M-LOG-INTAKE-SERVICE (process_batch)
#   - M-OBSERVABILITY-LOGGING (log_event)
# side_effects:
#   - writes redacted logs to stdout via log_event
# invariants:
#   - auth is optional (accept pre-auth logs for crash debugging)
#   - validates envelope structure per §8.2
#   - redacts PII before forwarding
# failure_policy:
#   - service error -> 500
# END_MODULE_CONTRACT: M-API-LOG-INTAKE

from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import require_session_optional
from app.core.logging import log_event
from app.db.session import get_session
from app.services.log_intake import LogIntakeService

router = APIRouter()


# START_BLOCK: ROUTE_LOG_INTAKE
class CanonEnvelope(BaseModel):
    """Canonical log envelope per §8.2."""

    ts: str
    level: str = Field(pattern=r"^(debug|info|warn|error|fatal)$")
    env: str = Field(default="dev")
    service: str = Field(default="web")
    service_version: str = Field(default="dev")
    slice: str = Field(default="")
    module: str = Field(default="")
    block: str = Field(default="")
    event: str
    correlation_id: str = Field(default="")
    msg: str | None = None
    session_id: str | None = None
    user_id_hash: str | None = None
    payload: dict[str, Any] | None = None
    error: dict[str, Any] | None = None
    duration_ms: float | None = None
    http: dict[str, Any] | None = None
    operation_id: str | None = None
    phase: str | None = None


class LogBatch(BaseModel):
    """Batch of canonical log envelopes."""

    envelopes: list[CanonEnvelope]


@router.post("/api/_log")
async def intake_logs(
    batch: LogBatch,
    db: AsyncSession = Depends(get_session),
    current_user = Depends(require_session_optional),
) -> dict[str, int]:
    """
    Accept log batch from frontend. Auth is optional — logs before
    authentication are accepted for crash debugging.

    W-1.7: Canon envelope validation, PII redaction, forward to stdout.
    """
    service = LogIntakeService(db)

    user_id = current_user.id if current_user else uuid.uuid4()

    try:
        result = await service.process_batch(
            user_id=user_id,
            envelopes=[e.model_dump(exclude_none=True) for e in batch.envelopes],
        )

        return {
            "accepted": result["accepted"],
            "rejected": result["rejected"],
        }

    except Exception as e:
        log_event(
            "system.error",
            level="error",
            msg=f"Log intake failed: {type(e).__name__}",
            payload={"error": str(e)[:200]},
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Log intake failed",
        ) from e


# END_BLOCK: ROUTE_LOG_INTAKE
