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

// Фиксированный «сегодняшний день» для демо/MVP.
// В продакшене поменяется на new Date().
export const TODAY = new Date(2025, 7, 18) // 18 августа 2025

export function stripTime(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth(), d.getDate())
}

export function sameDay(a: Date, b: Date): boolean {
  return (
    a.getFullYear() === b.getFullYear() &&
    a.getMonth() === b.getMonth() &&
    a.getDate() === b.getDate()
  )
}

export function addDays(d: Date, days: number): Date {
  const next = new Date(d)
  next.setDate(next.getDate() + days)
  return next
}
