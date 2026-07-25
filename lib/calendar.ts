// ############################################################################
// AI_HEADER: MODULE_LIB_CALENDAR
// ROLE: Pure calendar matrix utilities, date keys, and day status labels.
// DEPENDENCIES: lib/contracts/calendar
// GRACE_ANCHORS: [CALENDAR_UTILITIES]
// SLICE: SLICE-TODAY-CALENDAR
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-CALENDAR
// purpose: Pure calendar matrix utilities, date keys, and day status labels.
// owns:
//   - lib/calendar.ts
// inputs: Date, year, month numbers
// outputs: statusLabel, dateKey string, monthMatrix 7x6 cells array, monthDiff
// dependencies: lib/contracts/calendar
// side_effects: none (pure)
// emitted_logs: none
// invariants:
//   - monthMatrix returns exactly 42 MonthCell entries starting on Monday
// failure_policy: none
// END_MODULE_CONTRACT: M-LIB-CALENDAR

// START_MODULE_MAP: M-LIB-CALENDAR
// public_entrypoints:
//   - statusLabel
//   - dateKey
//   - monthMatrix
//   - monthDiff
// semantic_blocks:
//   - CALENDAR_UTILITIES: statusLabel, dateKey, monthMatrix, monthDiff helper functions
// owned_tests:
//   - __tests__/lib/calendar.test.ts
// END_MODULE_MAP: M-LIB-CALENDAR

/**
 * Чистые календарные утилиты + контракт «тона дня».
 *
 * Типы статусов определены в контрактах (lib/contracts/calendar.ts).
 * Здесь только утилиты — без данных и без бизнес-логики расчёта статуса.
 */

// Реэкспорт типов из контрактов
export type { DayStatus, DayStatusMap } from "@/lib/contracts/calendar"

// START_BLOCK: CALENDAR_UTILITIES
export function statusLabel(s: "tense" | "even" | "supportive"): string {
  // START_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.statusLabel
  // purpose: Convert day status string to localized Russian label.
  // inputs: s ("tense" | "even" | "supportive")
  // returns: string
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.statusLabel
  return s === "tense"
    ? "напряжённый"
    : s === "supportive"
      ? "поддерживающий"
      : "ровный"
}

/** ISO yyyy-mm-dd — для ключей в Record<dateKey, DayStatus> и инвалидации. */
export function dateKey(d: Date): string {
  // START_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.dateKey
  // purpose: Format Date object as ISO yyyy-mm-dd string key.
  // inputs: d (Date)
  // returns: string
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.dateKey
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
  // START_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.monthMatrix
  // purpose: Generate 7x6=42 cell month grid starting on Monday for calendar UI rendering.
  // inputs: year (number), month (number 0..11)
  // returns: MonthCell[]
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.monthMatrix
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

/** Разница в месяцах: a - b. Используется для clamping навигации по месяцах. */
export function monthDiff(a: Date, b: Date): number {
  // START_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.monthDiff
  // purpose: Calculate integer month difference between two dates.
  // inputs: a (Date), b (Date)
  // returns: number
  // side_effects: none
  // error_behavior: none
  // END_FUNCTION_CONTRACT: F-M-LIB-CALENDAR.monthDiff
  return (a.getFullYear() - b.getFullYear()) * 12 + (a.getMonth() - b.getMonth())
}
// END_BLOCK: CALENDAR_UTILITIES
