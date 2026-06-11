
// ############################################################################
// AI_HEADER: MODULE_LIB_DATE
// ROLE: Tests — date.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for date.ts behavior
// owns:
//   - lib/date.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-LIB-DATE
// wave: W-2.7
// purpose: Date utilities (migrated from legacy)

/** Сериализация даты в URL-параметр YYYY-MM-DD (локальное время). */
export function toDateParam(d: Date): string {
  const y = d.getFullYear()
  const m = String(d.getMonth() + 1).padStart(2, "0")
  const day = String(d.getDate()).padStart(2, "0")
  return `${y}-${m}-${day}`
}

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

/** «18 августа» */
export function formatDayMonth(d: Date): string {
  return `${d.getDate()} ${MONTHS_RU_GEN[d.getMonth()]}`
}

/** «18 августа 2025» */
export function formatLong(d: Date): string {
  return `${d.getDate()} ${MONTHS_RU_GEN[d.getMonth()]} ${d.getFullYear()}`
}

/** День недели понедельник-1 … воскресенье-7 → индекс 0..6 для WEEKDAYS_* */
export function mondayFirstIndex(d: Date): number {
  return (d.getDay() + 6) % 7
}

/** Понедельник той недели, в которую попадает дата. */
export function startOfWeek(d: Date): Date {
  const idx = mondayFirstIndex(d)
  const res = new Date(d.getFullYear(), d.getMonth(), d.getDate() - idx)
  return res
}

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
