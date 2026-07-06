
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
export const BackendDayStatusSchema = z.enum(["supportive", "steady", "tense"])

export const CalendarAccessSchema = z.object({
  state: z.enum(["full", "preview", "locked"]),
  reason: z.enum([
    "active_referral_days",
    "active_subscription",
    "expired_access",
    "outside_access_window",
  ]).nullable().optional(),
  referralDaysLeft: z.number().int().nullable().optional(),
  subscriptionActive: z.boolean().nullable().optional(),
  accessUntil: z.string().nullable().optional(),
})

export const CalendarLunarFieldsSchema = z.object({
  phase: z.string().nullable().optional(),
  illumination: z.number().nullable().optional(),
  moonSign: z.string().nullable().optional(),
  lunarDay: z.number().int().nullable().optional(),
  voidOfCourse: z.boolean().nullable().optional(),
})

export const CalendarDayReadModelSchema = z.object({
  date: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  dayNumber: z.number().int(),
  isCurrentMonth: z.boolean(),
  isToday: z.boolean(),
  disabled: z.boolean(),
  dayStatus: BackendDayStatusSchema.nullable().optional(),
  access: CalendarAccessSchema.nullable().optional(),
  lunar: CalendarLunarFieldsSchema.default({}),
})

export const CalendarPayloadReadModelSchema = z.object({
  meta: z.object({
    schemaVersion: z.literal("calendar/v1"),
    contractVersion: z.number().int(),
    generatedAt: z.string(),
  }),
  month: z.string().regex(/^\d{4}-\d{2}$/),
  title: z.string(),
  allowedRange: z.object({
    from: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
    to: z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  }),
  days: z.array(CalendarDayReadModelSchema),
})

/** Record<dateKey, DayStatus> — маппинг yyyy-mm-dd -> тон */
export const DayStatusMapSchema = z.record(
  z.string().regex(/^\d{4}-\d{2}-\d{2}$/),
  DayStatusSchema
)

export type DayStatus = z.infer<typeof DayStatusSchema>
export type DayStatusMap = z.infer<typeof DayStatusMapSchema>
export type BackendDayStatus = z.infer<typeof BackendDayStatusSchema>
export type CalendarDayReadModel = z.infer<typeof CalendarDayReadModelSchema>
export type CalendarPayloadReadModel = z.infer<typeof CalendarPayloadReadModelSchema>

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

export function validateCalendarPayloadReadModel(data: unknown): CalendarPayloadReadModel {
  return CalendarPayloadReadModelSchema.parse(data)
}
