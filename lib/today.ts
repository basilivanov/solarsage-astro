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
  TodayPayload,
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
