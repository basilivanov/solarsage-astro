/**
 * API-фасад для справочника городов.
 *
 * Компоненты ходят сюда, никогда напрямую в fixtures.
 * Переключение между fixtures и реальным API — через ENV.
 *
 * Когда появится геокодер:
 *
 *   export async function searchCities(query: string): Promise<City[]> {
 *     const res = await fetch(`${API_BASE_URL}/cities?q=${encodeURIComponent(query)}`)
 *     if (!res.ok) throw new Error(...)
 *     return validateCities(await res.json())
 *   }
 */

import { type City } from "@/lib/contracts/city"
import { USE_FIXTURES } from "./config"

export type { City }

// ---------------------------------------------------------------------------
// Public API
// ---------------------------------------------------------------------------

export function searchCities(query: string, limit?: number): City[] {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { searchCitiesFixture } = require("./cities.fixtures") as typeof import("./cities.fixtures")
    return searchCitiesFixture(query, limit)
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

export function getPopularCities(): string[] {
  if (USE_FIXTURES) {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const { getPopularCitiesFixture } = require("./cities.fixtures") as typeof import("./cities.fixtures")
    return getPopularCitiesFixture()
  }

  // Production stub
  throw new Error(
    "Production API not implemented. Set NEXT_PUBLIC_USE_FIXTURES=true for development."
  )
}

// ---------------------------------------------------------------------------
// Async versions for future backend integration
// ---------------------------------------------------------------------------

export async function searchCitiesAsync(
  query: string,
  limit?: number,
): Promise<City[]> {
  if (USE_FIXTURES) {
    const { searchCitiesFixture } = await import("./cities.fixtures")
    return searchCitiesFixture(query, limit)
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}

export async function getPopularCitiesAsync(): Promise<string[]> {
  if (USE_FIXTURES) {
    const { getPopularCitiesFixture } = await import("./cities.fixtures")
    return getPopularCitiesFixture()
  }

  // TODO: Implement real API call
  throw new Error("Production API not implemented")
}
