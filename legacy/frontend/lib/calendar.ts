/**
 * Чистые календарные утилиты + контракт «тона дня».
 *
 * Типы статусов определены в контрактах (lib/contracts/calendar.ts).
 * Здесь только утилиты — без данных и без бизнес-логики расчёта статуса.
 */

// Реэкспорт типов из контрактов
export type { DayStatus, DayStatusMap } from "@/lib/contracts/calendar"

export function statusLabel(s: "tense" | "even" | "supportive"): string {
  return s === "tense"
    ? "напряжённый"
    : s === "supportive"
      ? "поддерживающий"
      : "ровный"
}

/** ISO yyyy-mm-dd — для ключей в Record<dateKey, DayStatus> и инвалидации. */
export function dateKey(d: Date): string {
  const yyyy = d.getFullYear()
  const mm = String(d.getMonth() + 1).padStart(2, "0")
  const dd = String(d.getDate()).padStart(2, "0")
  return `${yyyy}-${mm}-${dd}`
}

export type MonthCell = { date: Date; inMonth: boolean }

/**
 * Сетка месяца 7×6 = 42 ячейки, начинается с понедельника.
 * Включает «хвосты» соседних месяцев — чтобы UI рендерил полный grid без условий.
 */
export function monthMatrix(year: number, month: number): MonthCell[] {
  const first = new Date(year, month, 1)
  const startOffset = (first.getDay() + 6) % 7
  const daysInMonth = new Date(year, month + 1, 0).getDate()

  const cells: MonthCell[] = []

  for (let i = startOffset - 1; i >= 0; i--) {
    cells.push({ date: new Date(year, month, -i), inMonth: false })
  }
  for (let day = 1; day <= daysInMonth; day++) {
    cells.push({ date: new Date(year, month, day), inMonth: true })
  }
  while (cells.length < 42) {
    const last = cells[cells.length - 1].date
    const next = new Date(last)
    next.setDate(last.getDate() + 1)
    cells.push({ date: next, inMonth: false })
  }

  return cells
}

/** Разница в месяцах: a - b. Используется для clamping навигации по месяцам. */
export function monthDiff(a: Date, b: Date): number {
  return (a.getFullYear() - b.getFullYear()) * 12 + (a.getMonth() - b.getMonth())
}
