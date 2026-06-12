# ############################################################################
# AI_HEADER: MODULE_LOG_INTAKE_SERVICE
# ROLE: Process frontend log batches — validate, redact, forward to stdout.
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-LOG-INTAKE-SERVICE
# purpose: Service layer for processing frontend log envelopes. Validates
#   structure per §8.2, redacts PII, and forwards the SAME envelope to stdout
#   (preserving all original fields) without rebuilding.
# owns:
#   - apps/api/app/services/log_intake.py
# inputs:
#   - user_id: UUID (for correlation and rate limiting)
#   - envelopes: List[Dict[str, Any]] (canonical log envelopes from frontend)
# outputs:
#   - {"accepted": int, "rejected": int}
# dependencies:
#   - M-OBSERVABILITY-REDACTOR (redact_dict)
# side_effects:
#   - writes to stdout via direct JSON emit
# invariants:
#   - validates required fields: ts, level, event, service
#   - redacts PII before forwarding
#   - preserves ALL original envelope fields (slice, module, block, etc.)
#   - never throws on individual envelope errors (counts as rejected)
#   - never clears/modifies request-level contextvars
# failure_policy:
#   - invalid envelope -> rejected count incremented
#   - redaction error -> rejected count incremented
# END_MODULE_CONTRACT: M-LOG-INTAKE-SERVICE

# START_MODULE_MAP: M-LOG-INTAKE-SERVICE
# public_entrypoints:
#   - LogIntakeService.process_batch
# semantic_blocks:
#   - PROCESS_BATCH: process frontend log envelopes
# END_MODULE_MAP: M-LOG-INTAKE-SERVICE

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.redactor import redact_dict


REQUIRED_FIELDS = {
    "ts", "level", "env", "service", "service_version",
    "slice", "module", "block", "event", "correlation_id"
}


# START_BLOCK: PROCESS_BATCH
class LogIntakeService:
    """Service for processing frontend logs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def process_batch(
        self,
        user_id: uuid.UUID,
        envelopes: list[dict[str, Any]],
    ) -> dict[str, int]:
        # START_FUNCTION_CONTRACT: F-M-LOG-INTAKE-SERVICE.process_batch
        # purpose: Process frontend log batch: validate, redact, forward to stdout.
        # inputs: user_id (UUID), envelopes (list[dict])
        # returns: {"accepted": count, "rejected": count}
        # side_effects: writes redacted envelopes to stdout as JSON lines
        # emitted_logs: system.error on invalid envelopes (rejected)
        # error_behavior: never throws on individual envelope errors; counts as rejected
        # END_FUNCTION_CONTRACT: F-M-LOG-INTAKE-SERVICE.process_batch
        """
        Process a batch of frontend log envelopes.

        Each valid envelope is redacted and emitted directly to stdout
        as a complete JSON line (preserving all original canon fields).

        Args:
            user_id: User ID (for correlation and rate limiting)
            envelopes: List of canonical log envelopes from frontend

        Returns:
            {"accepted": count, "rejected": count}
        """
        accepted = 0
        rejected = 0

        for envelope in envelopes:
            try:
                # Validate required fields
                if not all(f in envelope for f in REQUIRED_FIELDS):
                    rejected += 1
                    self._emit_rejected(accepted, rejected)
                    continue

                # Redact PII — preserve all keys, just mask values
                redacted = redact_dict(envelope)

                # Emit the SAME redacted envelope directly to stdout
                # Do NOT rebuild via log_event() — preserve original fields
                self._emit_line(redacted)

                accepted += 1

            except Exception:
                rejected += 1

        return {"accepted": accepted, "rejected": rejected}

    def _emit_line(self, data: dict[str, Any]) -> None:
        """Write a JSON line directly to stdout using the centralized logger helper."""
        from app.core.logging import _emit
        _emit(data)

    def _emit_rejected(self, accepted: int, rejected: int) -> None:
        """Emit a backend-level warning about rejected envelope."""
        from app.core.logging import log_event
        log_event(
            "system.error",
            level="warn",
            msg="Log intake rejected: invalid envelope",
            payload={
                "missing_fields": [f for f in REQUIRED_FIELDS],
            },
        )


# END_BLOCK: PROCESS_BATCH
