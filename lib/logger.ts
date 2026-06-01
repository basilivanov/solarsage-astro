/**
 * Frontend structured logger for production monitoring.
 *
 * Usage:
 *   Logger.log('user_action', { action: 'click', button: 'submit' })
 *   Logger.error('api_error', error, { endpoint: '/api/profile' })
 *
 * WAVE: W-2.7
 */

export interface LogData {
  [key: string]: any
}

export class Logger {
  /**
   * Log an event with optional data.
   */
  static log(event: string, data?: LogData): void {
    const logData = {
      timestamp: new Date().toISOString(),
      event,
      level: 'info',
      ...data,
    }

    // Console log in development
    if (process.env.NODE_ENV !== 'production') {
      console.log('[LOG]', event, data)
    } else {
      console.log(JSON.stringify(logData))
    }

    // Send to backend for aggregation (fire and forget)
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
      fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      }).catch(() => {
        // Silent fail - don't break user experience
      })
    }
  }

  /**
   * Log an error with stack trace.
   */
  static error(event: string, error: Error, data?: LogData): void {
    const logData = {
      timestamp: new Date().toISOString(),
      event,
      level: 'error',
      error: error.message,
      stack: error.stack,
      ...data,
    }

    // Console error in development
    if (process.env.NODE_ENV !== 'production') {
      console.error('[ERROR]', event, error, data)
    } else {
      console.error(JSON.stringify(logData))
    }

    // Send to backend for aggregation (fire and forget)
    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
      fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      }).catch(() => {
        // Silent fail
      })
    }
  }

  /**
   * Log a warning.
   */
  static warn(event: string, data?: LogData): void {
    const logData = {
      timestamp: new Date().toISOString(),
      event,
      level: 'warning',
      ...data,
    }

    if (process.env.NODE_ENV !== 'production') {
      console.warn('[WARN]', event, data)
    } else {
      console.warn(JSON.stringify(logData))
    }

    if (typeof window !== 'undefined' && process.env.NODE_ENV === 'production') {
      fetch('/api/logs', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(logData),
      }).catch(() => {})
    }
  }
}
