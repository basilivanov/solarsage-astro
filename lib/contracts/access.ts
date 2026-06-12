
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_ACCESS
// ROLE: UI — access
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI access — component
// owns:
//   - lib/contracts/access.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
/**
 * Zod-контракт для Access (подписка/доступ).
 *
 * Единственный источник правды о форме данных. И моки, и будущий бэкенд
 * обязаны возвращать данные, которые проходят эту валидацию.
 */

import { z } from "zod"

export const AccessStateSchema = z.enum(["trial", "subscription", "expired", "none"])

export const AccessInfoSchema = z.object({
  state: AccessStateSchema,
  hasAccess: z.boolean(),
  /** Включительные границы окна доступа (start <= day <= end), Date или null */
  accessStart: z.date().nullable(),
  accessEnd: z.date().nullable(),
  /** Сколько дней осталось до конца окна (включая сегодня) */
  daysLeft: z.number().int().min(0),
})

export type AccessState = z.infer<typeof AccessStateSchema>
export type AccessInfo = z.infer<typeof AccessInfoSchema>

/**
 * Валидирует AccessInfo и выбрасывает при несоответствии.
 * Используется для runtime-проверки данных из моков и будущего бэка.
 */
export function validateAccessInfo(data: unknown): AccessInfo {
  return AccessInfoSchema.parse(data)
}
