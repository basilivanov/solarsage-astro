
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_PROFILE
// ROLE: UI — profile
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI profile — component
// owns:
//   - lib/contracts/profile.ts
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
 * Zod-контракт для Profile (профиль пользователя).
 *
 * Единственный источник правды о форме данных профиля.
 */

import { z } from "zod"

export const BirthDatePartsSchema = z.object({
  day: z.union([z.literal(""), z.string().regex(/^\d{1,2}$/)]),
  month: z.union([z.literal(""), z.string().regex(/^\d{1,2}$/)]),
  year: z.union([z.literal(""), z.string().regex(/^\d{4}$/)]),
})

export const BirthTimePartsSchema = z.object({
  hours: z.string(),
  minutes: z.string(),
  unknown: z.boolean(),
})

export const ProfileLocationSchema = z.object({
  city: z.string(),
  lat: z.number().nullable(),
  lon: z.number().nullable(),
  timezone: z.string().nullable(),
})

export const ProfileSchema = z.object({
  firstName: z.string().default(""),
  birthDate: BirthDatePartsSchema,
  birthTime: BirthTimePartsSchema,
  birthPlace: z.string(),
  currentCity: z.string(),
  birthdayCity: z.string(),
  birthLocation: ProfileLocationSchema.nullable().default(null),
  currentLocation: ProfileLocationSchema.nullable().default(null),
  birthdayLocation: ProfileLocationSchema.nullable().default(null),
  gender: z.enum(["male", "female"]).nullable().default(null),
  isOnboarded: z.boolean().default(false),
  /** birthPlace == currentCity (чекбокс «сейчас живу там же») */
  sameAsBirth: z.boolean(),
  /** currentCity == birthdayCity (чекбокс «ДР проведу там же») */
  birthdaySameAsCurrent: z.boolean(),
})

export type BirthDateParts = z.infer<typeof BirthDatePartsSchema>
export type BirthTimeParts = z.infer<typeof BirthTimePartsSchema>
export type ProfileLocation = z.infer<typeof ProfileLocationSchema>
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
