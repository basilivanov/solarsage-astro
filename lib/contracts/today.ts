
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY
// ROLE: UI — today
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI today — component
// owns:
//   - lib/contracts/today.ts
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
// module: M-CONTRACTS-TODAY
// wave: W-2.7
// purpose: Today contracts (migrated from legacy)

/**
 * Zod-контракт для Today (данные дня).
 *
 * Единственный источник правды о форме данных экрана дня.
 */

import { z } from "zod"

export const DayStatusSchema = z.enum(["supportive", "steady", "tense"]);

export type DayStatus = z.infer<typeof DayStatusSchema>;

export const AdaptedTopFlagSchema = z.object({
  /** Имя иконки для отображения */
  iconName: z.string().min(1),
  /** Короткий заголовок флага */
  title: z.string().min(1),
  /** Краткое описание-подпись */
  summary: z.string().min(1),
});

export type AdaptedTopFlag = z.infer<typeof AdaptedTopFlagSchema>;

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
  paragraphs: z.array(z.string().min(1)),
  bullets: z.array(z.string().min(1)).optional(),
}).refine(
  (section) => section.paragraphs.length > 0 || (section.bullets?.length ?? 0) > 0,
  { message: "why section must contain paragraphs or bullets" },
)

export const TodayPayloadSchema = z.object({
  /** ISO yyyy-mm-dd — для кэша, deeplink'ов, инвалидации SWR. */
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  /** Заголовок дня от LLM */
  headline: z.string(),
  /** Общий статус дня */
  dayStatus: DayStatusSchema,
  /** Флаги / карточки дня (топ-сигналы) */
  topFlags: z.array(AdaptedTopFlagSchema),
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
export type AdaptedTodayPayload = z.infer<typeof TodayPayloadSchema>

export function validateAdaptedTodayPayload(data: unknown): AdaptedTodayPayload {
  return TodayPayloadSchema.parse(data)
}
