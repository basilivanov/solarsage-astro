// ############################################################################
// AI_HEADER: MODULE_LIB_TODAY
// ROLE: UI — today date constant and calendar utilities
// DEPENDENCIES: lib/contracts/today
// GRACE_ANCHORS: [TODAY_CONSTANTS, DATE_UTILITIES]
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-TODAY
// purpose: Today date constant and date utility functions for Today screen navigation.
// owns:
//   - lib/today.ts
// inputs: Date objects
// outputs: Date manipulation helpers and TODAY date constant
// dependencies: lib/contracts/today
// side_effects: none (pure)
// emitted_logs: none
// invariants:
//   - TODAY evaluates to current Date instance
// failure_policy: none
// END_MODULE_CONTRACT: M-LIB-TODAY

// START_MODULE_MAP: M-LIB-TODAY
// public_entrypoints:
//   - TODAY
//   - stripTime
//   - sameDay
//   - addDays
// semantic_blocks:
//   - TODAY_CONSTANTS: date constants
//   - DATE_UTILITIES: stripTime, sameDay, addDays helper functions
// owned_tests:
//   - __tests__/lib/today.test.ts
// END_MODULE_MAP: M-LIB-TODAY

/**
 * Today — утилиты и типы для экрана дня.
 *
 * Типы данных определены в контрактах (lib/contracts/today.ts).
 * Здесь только календарные утилиты и константы.
 */

// Реэкспорт типов из контрактов
export type {
  TodayNote,
  TodayReading,
  TodayWhySection,
  TodayWhySection as TodayWhySectionUI,
  AdaptedTodayPayload,
  AdaptedTopFlag,
  DayStatus,
} from "@/lib/contracts/today"

// START_BLOCK: TODAY_CONSTANTS
/**
 * Current date (today) as a Date object.
 * Used for redirecting to /day/today after onboarding.
 */
export const TODAY = new Date()
// END_BLOCK: TODAY_CONSTANTS

// START_BLOCK: DATE_UTILITIES
/**
 * Strip time from date, keeping only year/month/day
 */
export function stripTime(d: Date): Date {
  // START_FUNCTION_CONTRACT: F-M-LIB-TODAY.stripTime
  // purpose: Return a new Date instance with time components reset to 00:00:00.
  // inputs: d (Date)
  // returns: Date
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-TODAY.stripTime
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

/**
 * Check if two dates are the same day
 */
export function sameDay(a: Date, b: Date): boolean {
  // START_FUNCTION_CONTRACT: F-M-LIB-TODAY.sameDay
  // purpose: Check whether two Date objects represent the same calendar day.
  // inputs: a (Date), b (Date)
  // returns: boolean
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-TODAY.sameDay
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

/**
 * Add days to a date
 */
export function addDays(d: Date, days: number): Date {
  // START_FUNCTION_CONTRACT: F-M-LIB-TODAY.addDays
  // purpose: Return a new Date instance shifted by specified number of days.
  // inputs: d (Date), days (number)
  // returns: Date
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-TODAY.addDays
  const next = new Date(d)
  next.setDate(next.getDate() + days)
  return next
}
// END_BLOCK: DATE_UTILITIES
