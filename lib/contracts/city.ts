
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CITY
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/contracts/city.ts
// owns:
//   - lib/contracts/city.ts
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
 * Zod-контракт для City (справочник городов).
 *
 * Единственный источник правды о форме данных города.
 */

import { z } from "zod"

export const CitySchema = z.object({
  name: z.string().min(1),
  country: z.string().min(1),
  region: z.string().optional(),
  lat: z.number().optional(),
  lon: z.number().optional(),
  timezone: z.string().optional(),
})

export const CityListSchema = z.array(CitySchema)

export type City = z.infer<typeof CitySchema>

/**
 * Format city as display string: "Name, Country"
 */
export function formatCity(city: City | string): string {
  if (typeof city === 'string') return city
  return `${city.name}, ${city.country}`
}

/**
 * Валидирует массив городов и выбрасывает при несоответствии.
 */
export function validateCities(data: unknown): City[] {
  return CityListSchema.parse(data)
}

/**
 * Валидирует один город.
 */
export function validateCity(data: unknown): City {
  return CitySchema.parse(data)
}
