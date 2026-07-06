import type {
  CheckinCreate,
  CheckinMetrics,
  CheckinResponse,
  YesterdayCheckinResponse,
} from "@/packages/contracts"

export type {
  CheckinCreate,
  CheckinMetrics,
  CheckinResponse,
  YesterdayCheckinResponse,
}

export type CheckinMood = 1 | 2 | 3 | 4 | 5
export type CheckinAccuracy = 1 | 2 | 3
export type CheckinEnergy = 1 | 2 | 3 | 4 | 5

export const CHECKIN_TAGS = [
  "work_win",
  "work_fail",
  "money_in",
  "money_out",
  "argument",
  "support",
  "tired",
  "energetic",
  "anxious",
  "calm",
  "focused",
  "scattered",
  "lucky",
  "unlucky",
  "social",
  "alone",
  "sport",
  "sleep_bad",
  "sleep_good",
] as const

export type CheckinTag = (typeof CHECKIN_TAGS)[number]

export const MOOD_OPTIONS = [
  { value: 1, emoji: "😫", label: "Тяжело" },
  { value: 2, emoji: "😕", label: "Сложно" },
  { value: 3, emoji: "😐", label: "Нормально" },
  { value: 4, emoji: "🙂", label: "Хорошо" },
  { value: 5, emoji: "🤩", label: "Отлично" },
] as const

export const ACCURACY_OPTIONS = [
  { value: 1, emoji: "×", label: "Мимо" },
  { value: 2, emoji: "~", label: "Частично" },
  { value: 3, emoji: "✓", label: "Попал" },
] as const

export const ENERGY_OPTIONS = [
  { value: 1, emoji: "🪫", label: "Нет сил" },
  { value: 2, emoji: "😴", label: "Усталость" },
  { value: 3, emoji: "🔋", label: "Ровно" },
  { value: 4, emoji: "⚡", label: "Бодро" },
  { value: 5, emoji: "↑", label: "Много" },
] as const

export const TAG_OPTIONS: Array<{
  value: CheckinTag
  emoji: string
  label: string
}> = [
  { value: "work_win", emoji: "💼", label: "Работа: победа" },
  { value: "work_fail", emoji: "↓", label: "Работа: сложно" },
  { value: "money_in", emoji: "₽", label: "Деньги пришли" },
  { value: "money_out", emoji: "−", label: "Расходы" },
  { value: "argument", emoji: "!", label: "Конфликт" },
  { value: "support", emoji: "+", label: "Поддержка" },
  { value: "tired", emoji: "😴", label: "Усталость" },
  { value: "energetic", emoji: "⚡", label: "Энергия" },
  { value: "anxious", emoji: "?", label: "Тревога" },
  { value: "calm", emoji: "·", label: "Спокойствие" },
  { value: "focused", emoji: "◉", label: "Фокус" },
  { value: "scattered", emoji: "…", label: "Рассеянность" },
  { value: "lucky", emoji: "✓", label: "Удача" },
  { value: "unlucky", emoji: "×", label: "Неудача" },
  { value: "social", emoji: "👥", label: "Общение" },
  { value: "alone", emoji: "○", label: "Одиноко" },
  { value: "sport", emoji: "🏃", label: "Спорт" },
  { value: "sleep_bad", emoji: "☾", label: "Плохой сон" },
  { value: "sleep_good", emoji: "☀", label: "Хороший сон" },
]
