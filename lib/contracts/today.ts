// AI_HEADER
// module: M-CONTRACTS-TODAY
// wave: W-2.7
// purpose: Today contracts (migrated from legacy)

/**
 * Zod-контракт для Today (данные дня).
 *
 * Единственный источник правды о форме данных экрана дня.
 */

import { z } from "zod"

export const IconNameSchema = z.enum([
  "moon",
  "orbit",
  "briefcase",
  "compass",
  "hourglass",
  "target",
  "layers",
  "trending-up",
  "leaf",
  "grid",
  "telescope",
  "list-checks",
  "zap",
  "sparkle",
  "check",
  "building",
])

export const TodayNoteHintSchema = z.object({
  meaning: z.string().min(1),
  whyImportant: z.string().min(1),
  howForMe: z.string().min(1),
})

export const TodayNoteSchema = z.object({
  id: z.string().min(1),
  iconName: z.string().min(1), // Более мягкая проверка — fallback на Compass в UI
  title: z.string().min(1),
  description: z.string().min(1),
  hint: TodayNoteHintSchema,
})

export const TodayReadingSchema = z.object({
  /** Абзацы разбора по порядку. Первый получает dropcap-стиль в UI. */
  paragraphs: z.array(z.string().min(1)).min(1),
})

export const TodayWhySectionSchema = z.object({
  id: z.string().min(1),
  iconName: z.string().min(1),
  title: z.string().min(1),
  paragraphs: z.array(z.string().min(1)).min(1),
  bullets: z.array(z.string()).optional(),
})

export const TodayPayloadSchema = z.object({
  /** ISO yyyy-mm-dd — для кэша, deeplink'ов, инвалидации SWR. */
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  notes: z.array(TodayNoteSchema),
  reading: TodayReadingSchema,
  why: z.array(TodayWhySectionSchema),
  /** Короткий «ключ дня», закрывающий блок «Почему так у меня». */
  keyInsight: z.string().min(1),
})

export type IconName = z.infer<typeof IconNameSchema>
export type TodayNote = z.infer<typeof TodayNoteSchema>
export type TodayReading = z.infer<typeof TodayReadingSchema>
export type TodayWhySection = z.infer<typeof TodayWhySectionSchema>
export type TodayPayload = z.infer<typeof TodayPayloadSchema>

/**
 * Валидирует TodayPayload и выбрасывает при несоответствии.
 */
export function validateTodayPayload(data: unknown): TodayPayload {
  return TodayPayloadSchema.parse(data)
}
