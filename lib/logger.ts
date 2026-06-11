
// ############################################################################
// AI_HEADER: MODULE_LIB_LOGGER
// ROLE: Lib — logger.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: logger
// owns:
//   - lib/logger.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: Logging via v2 logging spine
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * @deprecated Since W-1.6. Use lib/log/index.ts (logEvent, logger) instead.
 * Kept as a thin re-export shim for existing call sites.
 *
 * TODO(W-1.6): Remove this file and update all imports to @/lib/log.
 */

import { logger } from "./log/index";

export interface LogData {
  [key: string]: any
}

export class Logger {
  static log(event: string, data?: LogData): void {
    logger.info(event, { extra: data });
  }

  static error(event: string, error: Error, data?: LogData): void {
    logger.error(`${event}: ${error.message}`, { extra: { ...data, stack: error.stack } });
  }

  static warn(event: string, data?: LogData): void {
    logger.warn(event, { extra: data });
  }
}
