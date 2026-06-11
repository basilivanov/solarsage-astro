
// ############################################################################
// AI_HEADER: MODULE_API_CITIES
// ROLE: Lib — cities.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ####// START_MODULE_CONTRACT
// purpose: Library: cities
// owns:
//   - lib/api/cities.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: Logging via v2 logging spine
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT/**
 * API-фасад для справочника городов.
 *
 * Использует реальный GeoNames API через /api/geo/autocomplete.
 */

import { type City } from "@/lib/contracts/city"
import { searchCities as searchGeoNames, type GeoSuggestion } from "./geo"
import { logEvent } from "@/lib/log"

export type { City }

function geoSuggestionToCity(geo: GeoSuggestion): City {
  return {
    name: geo.name,
    country: geo.country || "Unknown",
    region: geo.admin1 || undefined,
    lat: geo.lat,
    lon: geo.lon,
    timezone: geo.timezone_id || undefined,
  }
}

export function searchCities(_query: string, _limit?: number): City[] {
  return []
}

export function getPopularCities(): City[] {
  return [
    { name: "Москва", country: "Россия", lat: 55.7558, lon: 37.6173, timezone: "Europe/Moscow" },
    { name: "Санкт-Петербург", country: "Россия", lat: 59.9343, lon: 30.3351, timezone: "Europe/Moscow" },
    { name: "Новосибирск", country: "Россия", lat: 55.0415, lon: 82.9346, timezone: "Asia/Novosibirsk" },
    { name: "Екатеринбург", country: "Россия", lat: 56.8389, lon: 60.6057, timezone: "Asia/Yekaterinburg" },
    { name: "Казань", country: "Россия", lat: 55.7879, lon: 49.1233, timezone: "Europe/Moscow" },
    { name: "Нижний Новгород", country: "Россия", lat: 56.2965, lon: 43.9361, timezone: "Europe/Moscow" },
  ]
}

export async function searchCitiesAsync(
  query: string,
  limit: number = 8,
): Promise<City[]> {
  try {
    const suggestions = await searchGeoNames(query, limit)
    return suggestions.map(geoSuggestionToCity)
  } catch (error) {
    logEvent("ui.fetch_failed", { error: String(error) }, { msg: "Failed to search cities", level: "error", slice: "W-GEO", module: "M-CITIES-API", block: "SEARCH_CITIES" })
    return []
  }
}

export async function getPopularCitiesAsync(): Promise<City[]> {
  return getPopularCities()
}
