
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CALENDAR
// ROLE: UI — calendar
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI calendar — component
// owns:
//   - lib/contracts/calendar.ts
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
// module: M-CONTRACTS-CALENDAR
// wave: W-2.7
// purpose: Calendar contracts (migrated from legacy)

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
