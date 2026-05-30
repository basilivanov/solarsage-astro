// ############################################################################
// AI_HEADER: MODULE_LOG_FRONTEND
// ROLE: Frontend logger with shipping to backend via POST /api/_log.
// DEPENDENCIES: lib/log/shipper
// GRACE_ANCHORS: [LOGGER_CLASS, LOG_METHODS]
// WAVE: W-1.6, W-1.7
// ############################################################################

// START_MODULE_CONTRACT: M-LOG-FRONTEND
// purpose: Provide structured logging for frontend with optional shipping to
//   backend. Logs to console in dev, ships to backend when enabled.
// owns:
//   - lib/log/index.ts
// inputs:
//   - message: string
//   - options: { correlation_id?, extra? }
// outputs:
//   - console logs (dev)
//   - POST /api/_log (when GRACE_LOG_SHIPPING enabled)
// dependencies:
//   - M-LOG-SHIPPER (getLogShipper)
// side_effects:
//   - console.log in development
//   - network requests when shipping enabled
// invariants:
//   - always logs to console in development
//   - ships to backend only when GRACE_LOG_SHIPPING=true
//   - envelope format matches §8.2
// failure_policy:
//   - shipper errors are handled internally (no throw)
// non_goals:
//   - no log levels beyond info/warn/error
//   - no sampling (deferred to W-CANON-LOG)
// END_MODULE_CONTRACT: M-LOG-FRONTEND

// START_MODULE_MAP: M-LOG-FRONTEND
// public_entrypoints:
//   - logger
//   - Logger (class)
// semantic_blocks:
//   - LOGGER_CLASS: Logger implementation
//   - LOG_METHODS: info/warn/error methods
// owned_tests:
//   - apps/api/tests/test_log_intake.py (e2e)
// END_MODULE_MAP: M-LOG-FRONTEND

import { getLogShipper } from "./shipper";

// START_BLOCK: LOGGER_CLASS
interface LogOptions {
  correlation_id?: string;
  extra?: Record<string, any>;
}

class Logger {
  private shipper = getLogShipper();

  info(message: string, options?: LogOptions): void {
    this.log("info", message, options);
  }

  warn(message: string, options?: LogOptions): void {
    this.log("warn", message, options);
  }

  error(message: string, options?: LogOptions): void {
    this.log("error", message, options);
  }

  private log(level: string, message: string, options?: LogOptions): void {
    const envelope = {
      timestamp: new Date().toISOString(),
      level,
      message,
      correlation_id: options?.correlation_id,
      extra: options?.extra,
    };

    // Console (dev)
    if (process.env.NODE_ENV === "development") {
      console.log(`[${level.toUpperCase()}]`, message, options?.extra);
    }

    // Ship to backend (W-1.7)
    this.shipper.enqueue(envelope);
  }
}

export const logger = new Logger();
// END_BLOCK: LOGGER_CLASS
