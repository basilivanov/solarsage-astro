
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_PROFILE
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/contracts/profile.ts
// owns:
//   - lib/contracts/profile.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

/**
 * Zod-контракт для Profile (профиль пользователя).
 *
 * Единственный источник правды о форме данных профиля.
 */

import { z } from "zod"

export const BirthDatePartsSchema = z.object({
  day: z.string().regex(/^\d{1,2}$/),
  month: z.string().regex(/^\d{1,2}$/),
  year: z.string().regex(/^\d{4}$/),
})

export const BirthTimePartsSchema = z.object({
  hours: z.string(),
  minutes: z.string(),
  unknown: z.boolean(),
})

export const ProfileSchema = z.object({
  birthDate: BirthDatePartsSchema,
  birthTime: BirthTimePartsSchema,
  birthPlace: z.string().min(1),
  currentCity: z.string().min(1),
  birthdayCity: z.string().min(1),
  gender: z.enum(["male", "female"]),
  /** birthPlace == currentCity (чекбокс «сейчас живу там же») */
  sameAsBirth: z.boolean(),
  /** currentCity == birthdayCity (чекбокс «ДР проведу там же») */
  birthdaySameAsCurrent: z.boolean(),
})

export type BirthDateParts = z.infer<typeof BirthDatePartsSchema>
export type BirthTimeParts = z.infer<typeof BirthTimePartsSchema>
export type Profile = z.infer<typeof ProfileSchema>

/**
 * Валидирует Profile и выбрасывает при несоответствии.
 */
export function validateProfile(data: unknown): Profile {
  return ProfileSchema.parse(data)
}

/**
 * Безопасная валидация — возвращает результат без исключения.
 */
export function safeValidateProfile(data: unknown) {
  return ProfileSchema.safeParse(data)
}
