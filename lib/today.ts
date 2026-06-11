
// ############################################################################
// AI_HEADER: MODULE_LIB_TODAY
// ROLE: UI — today
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TODAY-CALENDAR
// #########################################// START_MODULE_CONTRACT
// purpose: UI today — component
// owns:
//   - lib/today.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-LIB-TODAY
// wave: W-2.7
// purpose: Today date constant and utilities

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
  AdaptedTodayPayload,
} from "@/lib/contracts/today"

/**
 * Current date (today) as a Date object.
 * Used for redirecting to /day/today after onboarding.
 */
export const TODAY = new Date()

/**
 * Strip time from date, keeping only year/month/day
 */
export function stripTime(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

/**
 * Check if two dates are the same day
 */
export function sameDay(a: Date, b: Date): boolean {
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
  const next = new Date(d)
  next.setDate(next.getDate() + days)
  return next
}
