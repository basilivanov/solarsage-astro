/**
 * Zod-контракт для Calendar (тон дня).
 *
 * Единственный источник правды о форме данных календаря.
 */

import { z } from "zod"

export const DayStatusSchema = z.enum(["tense", "even", "supportive"])

/** Record<dateKey, DayStatus> — маппинг yyyy-mm-dd -> тон */
export const DayStatusMapSchema = z.record(
  z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  DayStatusSchema
)

export type DayStatus = z.infer<typeof DayStatusSchema>
export type DayStatusMap = z.infer<typeof DayStatusMapSchema>

/**
 * Валидирует DayStatus и выбрасывает при несоответствии.
 */
export function validateDayStatus(data: unknown): DayStatus {
  return DayStatusSchema.parse(data)
}

/**
 * Валидирует маппинг дней.
 */
export function validateDayStatusMap(data: unknown): DayStatusMap {
  return DayStatusMapSchema.parse(data)
}
