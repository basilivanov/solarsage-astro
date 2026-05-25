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
})

export const CityListSchema = z.array(CitySchema)

export type City = z.infer<typeof CitySchema>

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
