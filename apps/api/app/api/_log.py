# ############################################################################
# AI_HEADER: MODULE_API_LOG_INTAKE
# ROLE: HTTP surface for POST /api/_log — accepts frontend log batches.
# DEPENDENCIES: fastapi, sqlalchemy, app.services.log_intake
# GRACE_ANCHORS: [LOG_INTAKE_ENDPOINT]
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-API-LOG-INTAKE
# purpose: Accept log batches from frontend, forward to backend logging spine.
# owns:
#   - apps/api/app/api/_log.py
# inputs:
#   - POST /api/_log: LogBatch with canonical envelopes
#   - optional session for user_id correlation
# outputs:
#   - {"accepted": int, "rejected": int}
# dependencies:
#   - M-LOG-INTAKE-SERVICE
#   - M-DB-SESSION
#   - M-AUTH-DEPENDENCIES (optional)
# side_effects:
#   - emits redacted envelopes to stdout
# invariants:
#   - invalid envelopes are counted as rejected, never crash
# failure_policy:
#   - 500 on unexpected errors; individual envelope errors count as rejected
# non_goals:
#   - no log storage (forwarding only)
# END_MODULE_CONTRACT: M-API-LOG-INTAKE

# START_MODULE_MAP: M-API-LOG-INTAKE
# public_entrypoints:
#   - intake_logs
# semantic_blocks:
#   - LOG_INTAKE_ENDPOINT: POST /api/_log handler
# END_MODULE_MAP: M-API-LOG-INTAKE

from __future__ import annotations

import uuid
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from typing import Annotated, Any, Literal

from app.core.dependencies import require_session_optional
from app.core.logging import log_event
from app.core.logging_events import LogEventName
from app.db.session import get_session
from app.services.log_intake import LogIntakeService

router = APIRouter()


class CanonEnvelope(BaseModel):
    """Canonical log envelope per §8.2 — strict required fields."""

    ts: str
    level: Annotated[str, Field(pattern=r'^(debug|info|warn|error|fatal)$')]
    env: Literal["dev", "test", "staging", "prod"]
    service: Literal["api", "web", "solarsage", "worker"]
    service_version: Annotated[str, Field(min_length=1)]
    slice: Annotated[str, Field(min_length=1)]
    module: Annotated[str, Field(min_length=1)]
    block: Annotated[str, Field(min_length=1)]
    event: LogEventName
    correlation_id: Annotated[str, Field(min_length=1)]
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
    Accept log batch from frontend. Auth is optional.
    Each valid canonical envelope is redacted and forwarded to stdout
    preserving all original fields (slice, module, block, duration, etc.).
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
