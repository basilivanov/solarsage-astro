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
                    logger.warning(
                        "Log intake rejected: invalid envelope",
                        extra={"user_id": str(user_id)},
                    )
                    continue

                # Redact PII
                redacted = redact_dict(envelope)

                # Forward to stdout (backend logger)
                logger.info(
                    f"[FRONTEND] {redacted['message']}",
                    extra={
                        "user_id": str(user_id),
                        "correlation_id": redacted.get("correlation_id"),
                        "frontend_log": redacted,
                    },
                )

                accepted += 1

            except Exception as e:
                rejected += 1
                logger.error(
                    f"Log intake error: {e}",
                    extra={"user_id": str(user_id)},
                )

        return {"accepted": accepted, "rejected": rejected}

    def _validate_envelope(self, envelope: dict[str, Any]) -> bool:
        """
        Validate log envelope structure.

        Required fields per §8.2:
        - timestamp: ISO 8601 string
        - level: log level (info, warn, error)
        - message: log message

        Args:
            envelope: Log envelope to validate

        Returns:
            True if valid, False otherwise
        """
        required_fields = ["timestamp", "level", "message"]
        return all(field in envelope for field in required_fields)


# END_BLOCK: PROCESS_BATCH
