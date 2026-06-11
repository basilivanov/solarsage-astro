
// ############################################################################
// AI_HEADER: MODULE_LIB_LOGGER
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/logger.ts
// owns:
//   - lib/logger.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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
