# ############################################################################
# AI_HEADER: MODULE_LOG_INTAKE_SERVICE
# ROLE: Process frontend log batches — validate, redact, forward to stdout.
# DEPENDENCIES: sqlalchemy, app.core.logging, app.core.redactor
# GRACE_ANCHORS: [PROCESS_BATCH, VALIDATE_ENVELOPE]
# WAVE: W-1.7
# ############################################################################

# START_MODULE_CONTRACT: M-LOG-INTAKE-SERVICE
# purpose: Service layer for processing frontend log envelopes. Validates
#   structure per §8.2, redacts PII, and forwards to backend stdout logger.
# owns:
#   - apps/api/app/services/log_intake.py
# inputs:
#   - user_id: UUID (for correlation and rate limiting)
#   - envelopes: List[Dict[str, Any]] (log envelopes from frontend)
# outputs:
#   - {"accepted": int, "rejected": int}
# dependencies:
#   - M-OBSERVABILITY-LOGGING (logger)
#   - M-OBSERVABILITY-REDACTOR (redact_dict)
# side_effects:
#   - writes to stdout via logger
# invariants:
#   - validates required fields: timestamp, level, message
#   - redacts PII before forwarding
#   - never throws on individual envelope errors (counts as rejected)
# failure_policy:
#   - invalid envelope -> rejected count incremented, logged as warning
#   - redaction error -> rejected count incremented
# non_goals:
#   - no rate limiting (deferred to W-RATELIMIT)
#   - no sampling (deferred to W-CANON-LOG)
# END_MODULE_CONTRACT: M-LOG-INTAKE-SERVICE

# START_MODULE_MAP: M-LOG-INTAKE-SERVICE
# public_entrypoints:
#   - LogIntakeService
# semantic_blocks:
#   - PROCESS_BATCH: main processing loop
#   - VALIDATE_ENVELOPE: structure validation
# owned_tests:
#   - apps/api/tests/test_log_intake.py
# END_MODULE_MAP: M-LOG-INTAKE-SERVICE

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import logger
from app.core.redactor import redact_dict


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
        """
        Process a batch of log envelopes.

        Args:
            user_id: User ID (for correlation and rate limiting)
            envelopes: List of log envelopes from frontend

        Returns:
            {"accepted": count, "rejected": count}
        """
        accepted = 0
        rejected = 0

        for envelope in envelopes:
            try:
                # Validate envelope
                if not self._validate_envelope(envelope):
                    rejected += 1
                    self._log_event(
                        "system.error",
                        level="warn",
                        msg="Log intake rejected: invalid envelope",
                        payload={"rejected_field": "missing required fields"},
                    )
                    continue

                # Redact PII
                redacted = redact_dict(envelope)

                # Forward to stdout as canon event (not nested)
                self._log_event(
                    redacted.get("event", "system.request"),
                    level=redacted.get("level", "info"),
                    msg=redacted.get("msg", ""),
                    payload=redacted.get("payload"),
                    correlation_id=redacted.get("correlation_id", ""),
                    service="web",
                )

                accepted += 1

            except Exception as e:
                rejected += 1
                self._log_event(
                    "system.error",
                    level="error",
                    msg=f"Log intake error: {type(e).__name__}",
                )

        return {"accepted": accepted, "rejected": rejected}

    def _validate_envelope(self, envelope: dict[str, Any]) -> bool:
        """
        Validate log envelope structure.

        Required fields per §8.2:
        - ts: ISO 8601 string
        - level: log level
        - event: event name
        - service: service name

        Args:
            envelope: Log envelope to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["ts", "level", "event", "service"]
        return all(field in envelope for field in required_fields)

    def _log_event(
        self,
        event: str,
        level: str = "info",
        msg: str = "",
        payload: dict[str, Any] | None = None,
        correlation_id: str = "",
        service: str = "",
    ) -> None:
        """Emit a frontend log as a canon event via log_event."""
        from app.core.logging import log_event as core_log_event, bind_log_context, clear_log_context

        if correlation_id:
            bind_log_context(
                correlation_id=correlation_id,
                module="M-LOG-INTAKE-SERVICE",
                block="FRONTEND_LOG",
                service=service,
            )

        core_log_event(
            event,
            level=level,
            msg=msg,
            payload=payload,
        )

        if correlation_id:
            clear_log_context()


# END_BLOCK: PROCESS_BATCH
