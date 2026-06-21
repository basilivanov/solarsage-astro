
// ############################################################################
// AI_HEADER: MODULE_LIB_DATE
// ROLE: Date utility functions — serialization, parsing, formatting.
// DEPENDENCIES: none (pure functions)
// GRACE_ANCHORS: [DATE_PARSE, DATE_FORMAT]
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-DATE
// purpose: Pure date utility functions for serialization and formatting.
// owns:
//   - lib/date.ts
// inputs:
//   - Date objects or strings
// outputs:
//   - formatted date strings
// dependencies:
//   - none (pure functions)
// side_effects:
//   - none (pure functions)
// invariants:
//   - toDateParam returns YYYY-MM-DD format
//   - fromDateParam validates regex before parsing
// failure_policy:
//   - fromDateParam returns null for invalid input
// END_MODULE_CONTRACT: M-LIB-DATE

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.toDateParam
// purpose: Serialize a Date to YYYY-MM-DD URL parameter (local time).
// inputs: d (Date)
// returns: string in YYYY-MM-DD format
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.toDateParam
/** Сериализация даты в URL-параметр YYYY-MM-DD (локальное время). */
export function toDateParam(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.fromDateParam
// purpose: Parse YYYY-MM-DD URL parameter string to Date.
// inputs: s (string) — URL parameter value
// returns: Date | null — parsed Date or null for invalid input
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: returns null for invalid format; never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.fromDateParam
/** Парсинг URL-параметра YYYY-MM-DD → Date; возвращает null для мусора. */
export function fromDateParam(s: string): Date | null {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return null
  const [y, m, d] = s.split("-").map(Number)
  const date = new Date(y, m - 1, d)
  if (
    date.getFullYear() !== y ||
    date.getMonth() !== m - 1 ||
    date.getDate() !== d
  ) {
    return null
  }
  return date
}

export const MONTHS_RU_NOM = [
  "Январь",
  "Февраль",
  "Март",
  "Апрель",
  "Май",
  "Июнь",
  "Июль",
  "Август",
  "Сентябрь",
  "Октябрь",
  "Ноябрь",
  "Декабрь",
]

// Родительный падеж для форматов «18 августа»
export const MONTHS_RU_GEN = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
]

export const WEEKDAYS_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
export const WEEKDAYS_MINI = ["ПН", "ВТ", "СР", "ЧТ", "ПТ", "СБ", "ВС"]

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.formatDayMonth
// purpose: Format Date as «18 августа» (day + month in genitive).
// inputs: d (Date)
// returns: string — formatted date
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.formatDayMonth
/** «18 августа» */
export function formatDayMonth(d: Date): string {
  return `${d.getDate()} ${MONTHS_RU_GEN[d.getMonth()]}`
}

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.formatLong
// purpose: Format Date as «18 августа 2025» (full Russian date).
// inputs: d (Date)
// returns: string — formatted date with year
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.formatLong
/** «18 августа 2025» */
export function formatLong(d: Date): string {
  return `${d.getDate()} ${MONTHS_RU_GEN[d.getMonth()]} ${d.getFullYear()}`
}

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.mondayFirstIndex
// purpose: Convert JS getDay() (0=Sun) to Monday-first index (0=Mon).
// inputs: d (Date)
// returns: number — 0 (Mon) to 6 (Sun)
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.mondayFirstIndex
/** День недели понедельник-1 … воскресенье-7 → индекс 0..6 для WEEKDAYS_* */
export function mondayFirstIndex(d: Date): number {
  return (d.getDay() + 6) % 7
}

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.startOfWeek
// purpose: Get Monday (start of week) for the given date.
// inputs: d (Date)
// returns: Date — Monday 00:00 of that week
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.startOfWeek
/** Понедельник той недели, в которую попадает дата. */
export function startOfWeek(d: Date): Date {
  const idx = mondayFirstIndex(d)
  const res = new Date(d.getFullYear(), d.getMonth(), d.getDate() - idx)
  return res
}

// START_FUNCTION_CONTRACT: F-M-LIB-DATE.formatWeekRange
// purpose: Format week range as «18 – 24 авг» or «28 июл – 3 авг».
// inputs: start (Date) — Monday of the week
// returns: string — formatted week range in Russian
// side_effects: none (pure function)
// emitted_logs: none
// error_behavior: never raises
// END_FUNCTION_CONTRACT: F-M-LIB-DATE.formatWeekRange
/** Диапазон недели: «18 – 24 авг» или «28 июл – 3 авг» */
export function formatWeekRange(start: Date): string {
  const end = new Date(start)
  end.setDate(start.getDate() + 6)
  const ms = MONTHS_RU_GEN.map((m) => m.slice(0, 3))
  if (start.getMonth() === end.getMonth()) {
    return `${start.getDate()} – ${end.getDate()} ${ms[start.getMonth()]}`
  }
  return `${start.getDate()} ${ms[start.getMonth()]} – ${end.getDate()} ${ms[end.getMonth()]}`
}
