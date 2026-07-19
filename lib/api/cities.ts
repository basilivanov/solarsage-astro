
// ############################################################################
// AI_HEADER: FRONTEND_API_CITIES — city catalog and GeoNames result adapter.
// ROLE: City catalog/search adapter consumed by the onboarding city picker.
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-API-CITIES
// purpose: Provide static popular cities and adapt GeoSuggestion results to City.
// owns:
//   - lib/api/cities.ts
// inputs: query and optional limit.
// outputs: City exports and synchronous/asynchronous city arrays.
// dependencies: lib/contracts/city; lib/api/geo; lib/log logEvent.
// side_effects: async GeoNames-backed search and structured ui.fetch_failed log on caught failure.
// emitted_logs: ui.fetch_failed.
// invariants:
//   - Synchronous searchCities intentionally remains an empty compatibility result.
//   - Popular city names, coordinates and timezones remain unchanged.
//   - GeoSuggestion fields map to the current City fallback and optional fields.
//   - Failure log metadata remains slice=W-GEO, module=M-CITIES-API and block=SEARCH_CITIES without personal data.
// failure_policy: Async search catches, logs and returns an empty array; popular APIs do not throw.
// END_MODULE_CONTRACT: M-FRONTEND-API-CITIES

// START_MODULE_MAP: M-FRONTEND-API-CITIES
// public_entrypoints:
//   - City
//   - searchCities
//   - getPopularCities
//   - searchCitiesAsync
//   - getPopularCitiesAsync
// semantic_blocks:
//   - GEO_ADAPTER: map GeoSuggestion fields to City.
//   - SYNC_COMPAT_SEARCH: preserve the empty synchronous compatibility result.
//   - POPULAR_CATALOG: expose the stable popular city list.
//   - ASYNC_SEARCH: adapt GeoNames results; log and rethrow failures so the
//     sole consumer (CityPicker) can render an accessible error state.
//   - ASYNC_POPULAR_ALIAS: resolve the synchronous catalog asynchronously.
// owned_tests:
//   - __tests__/api/cities.test.ts
// END_MODULE_MAP: M-FRONTEND-API-CITIES
/**
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
  // Log and rethrow: the sole consumer (CityPicker) renders an accessible
  // error state, so failures must NOT degrade silently to an empty list.
  try {
    const suggestions = await searchGeoNames(query, limit)
    return suggestions.map(geoSuggestionToCity)
  } catch (error) {
    logEvent("ui.fetch_failed", { error: String(error) }, { msg: "Failed to search cities", level: "error", slice: "W-GEO", module: "M-CITIES-API", block: "SEARCH_CITIES" })
    throw error
  }
}

export async function getPopularCitiesAsync(): Promise<City[]> {
  return getPopularCities()
}
