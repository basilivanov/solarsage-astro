// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CHECKIN
// ROLE: Zod schemas for evening checkin
// DEPENDENCIES: zod
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// WAVE: W-8.1
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Zod validation schemas for evening checkin contracts.
// owns:
//   - lib/contracts/checkin.ts
// inputs: API response data
// outputs: Validated typed data
// dependencies: zod
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - mood is 1..5
//   - accuracy is 'miss' | 'partial' | 'hit' | null
//   - tags from closed set
// failure_policy: throw on invalid data
// END_MODULE_CONTRACT

import { z } from "zod"

export const CheckinMoodSchema = z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5)])
export type CheckinMood = z.infer<typeof CheckinMoodSchema>

export const CheckinAccuracySchema = z.enum(["miss", "partial", "hit"])
export type CheckinAccuracy = z.infer<typeof CheckinAccuracySchema>

export const CheckinEnergySchema = z.union([z.literal(1), z.literal(2), z.literal(3), z.literal(4), z.literal(5)])
export type CheckinEnergy = z.infer<typeof CheckinEnergySchema>

export const CHECKIN_TAGS = [
  "work_win", "work_fail", "money_in", "money_out",
  "argument", "support", "tired", "energetic",
  "anxious", "calm", "focused", "scattered",
  "lucky", "unlucky", "social", "alone",
  "sport", "sleep_bad", "sleep_good",
] as const
export type CheckinTag = typeof CHECKIN_TAGS[number]

export const CheckinTagSchema = z.enum(CHECKIN_TAGS)

export const CheckinCreateSchema = z.object({
  targetDate: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  mood: CheckinMoodSchema,
  accuracy: CheckinAccuracySchema.nullable().optional(),
  energy: CheckinEnergySchema.nullable().optional(),
  tags: z.array(CheckinTagSchema).nullable().optional(),
  note: z.string().max(500).nullable().optional(),
})
export type CheckinCreate = z.infer<typeof CheckinCreateSchema>

export const CheckinResponseSchema = z.object({
  id: z.number(),
  targetDate: z.string(),
  mood: z.number().min(1).max(5),
  accuracy: z.string().nullable(),
  energy: z.number().nullable(),
  tags: z.array(z.string()),
  note: z.string().nullable(),
  streak: z.number(),
  filledAt: z.string().nullable(),
  createdAt: z.string(),
})
export type CheckinResponse = z.infer<typeof CheckinResponseSchema>

export const YesterdayEchoSchema = z.object({
  hadCheckin: z.boolean(),
  mood: z.number().min(1).max(5).nullable().optional(),
  accuracy: z.string().nullable().optional(),
  closureText: z.string(),
  transition: z.enum(["released", "intensified", "shifted", "continued"]),
  yesterdayHighlight: z.string().nullable().optional(),
})
export type YesterdayEcho = z.infer<typeof YesterdayEchoSchema>

export const CheckinMetricsSchema = z.object({
  date: z.string(),
  eligible: z.number(),
  responded: z.number(),
  completed: z.number(),
  responseRate: z.number(),
  completionRate: z.number(),
  accuracyDistribution: z.record(z.string(), z.number()),
  moodAverage: z.number().nullable(),
  streakAvg: z.number(),
  streak7plusPct: z.number(),
})
export type CheckinMetrics = z.infer<typeof CheckinMetricsSchema>

// --- UI helpers ---

export const MOOD_OPTIONS = [
  { value: 1, emoji: "😫", label: "Ужасно" },
  { value: 2, emoji: "😕", label: "Так себе" },
  { value: 3, emoji: "😐", label: "Нормально" },
  { value: 4, emoji: "🙂", label: "Хорошо" },
  { value: 5, emoji: "🤩", label: "Отлично!" },
] as const

export const ACCURACY_OPTIONS = [
  { value: "miss", emoji: "❌", label: "Не совсем" },
  { value: "partial", emoji: "🤷", label: "Частично" },
  { value: "hit", emoji: "✅", label: "Да, попал!" },
] as const

export const TAG_OPTIONS: { value: CheckinTag; emoji: string; label: string }[] = [
  { value: "work_win", emoji: "💼", label: "Работа: победа" },
  { value: "work_fail", emoji: "📉", label: "Работа: провал" },
  { value: "money_in", emoji: "💰", label: "Деньги пришли" },
  { value: "money_out", emoji: "💸", label: "Деньги ушли" },
  { value: "argument", emoji: "💢", label: "Конфликт" },
  { value: "support", emoji: "🤝", label: "Поддержка" },
  { value: "tired", emoji: "😴", label: "Усталость" },
  { value: "energetic", emoji: "⚡", label: "Энергичность" },
  { value: "anxious", emoji: "😰", label: "Тревога" },
  { value: "calm", emoji: "🧘", label: "Спокойствие" },
  { value: "focused", emoji: "🎯", label: "Концентрация" },
  { value: "scattered", emoji: "🌫️", label: "Рассеянность" },
  { value: "lucky", emoji: "🍀", label: "Удача" },
  { value: "unlucky", emoji: "😵", label: "Неудача" },
  { value: "social", emoji: "👥", label: "Общение" },
  { value: "alone", emoji: "🧊", label: "Одиночество" },
  { value: "sport", emoji: "🏃", label: "Спорт" },
  { value: "sleep_bad", emoji: "🛌", label: "Плохой сон" },
  { value: "sleep_good", emoji: "😊", label: "Хороший сон" },
]
