# ############################################################################
# AI_HEADER: MODULE_OBSERVABILITY_LOGGING
# ROLE: Structured JSON logging with envelope format.
# DEPENDENCIES: logging, json, datetime
# GRACE_ANCHORS: [JSON_FORMATTER, LOGGER_SETUP]
# WAVE: W-1.6
# ############################################################################

# START_MODULE_CONTRACT: M-OBSERVABILITY-LOGGING
# purpose: Provide structured JSON logging with envelope format conforming to
#   observability canon §8.2 (simplified for MVP).
# owns:
#   - apps/api/app/core/logging.py
# inputs:
#   - log records from application code
#   - correlation_id from request context (optional)
# outputs:
#   - JSON-formatted log lines to stdout
# dependencies:
#   - standard library: logging, json, datetime
# side_effects:
#   - configures global logger instance
#   - writes to stdout
# invariants:
#   - all logs emitted as valid JSON
#   - timestamp in ISO 8601 format with Z suffix
#   - correlation_id included when present in record
# failure_policy:
#   - logging errors must not crash the application
# non_goals:
#   - no log aggregation (external concern)
#   - no sampling or rate limiting (deferred to W-CANON-LOG)
# END_MODULE_CONTRACT: M-OBSERVABILITY-LOGGING

import json
import logging
from datetime import UTC, datetime
from typing import Any


# START_BLOCK: JSON_FORMATTER
class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON envelope.

        Envelope structure:
        - timestamp: ISO 8601 with Z suffix
        - level: log level name (INFO, ERROR, etc.)
        - message: formatted message
        - module: source module name
        - function: source function name
        - line: source line number
        - correlation_id: request correlation ID (if present)
        - extra: additional fields (if present)
        """
        envelope = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add correlation_id if present
        if hasattr(record, "correlation_id"):
            envelope["correlation_id"] = record.correlation_id

        # Add extra fields
        if hasattr(record, "extra"):
            envelope["extra"] = record.extra

        return json.dumps(envelope)
# END_BLOCK: JSON_FORMATTER


# START_BLOCK: LOGGER_SETUP
def setup_logging() -> logging.Logger:
    """Setup structured logging.

    Returns:
        Configured logger instance with JSON formatter.
    """
    logger = logging.getLogger("astro")
    logger.setLevel(logging.INFO)

    # JSON handler for stdout
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)

    return logger


# Global logger instance
logger = setup_logging()
# END_BLOCK: LOGGER_SETUP
