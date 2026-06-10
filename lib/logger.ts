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
