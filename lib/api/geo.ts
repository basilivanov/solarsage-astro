
// ############################################################################
// AI_HEADER: MODULE_API_GEO
// ROLE: Lib — geo.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-FRONTEND-API-FACADES
// ############################################################################

// START_MODULE_CONTRACT
// purpose: API client for geo
// owns:
//   - lib/api/geo.ts
// inputs: Endpoint params, body
// outputs: Parsed response
// dependencies: local modules
// side_effects: Network calls to API
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

export interface GeoSuggestion {
  id: string
  name: string
  admin1: string | null
  country: string | null
  lat: number
  lon: number
  label: string
  timezone_id: string | null
}

export interface GeoTimezone {
  timezone_id: string | null
  gmt_offset: number | null
  dst_offset: number | null
  raw_offset: number | null
}

export async function searchCities(query: string, limit: number = 8): Promise<GeoSuggestion[]> {
  const response = await fetch(`/api/geo/autocomplete?q=${encodeURIComponent(query)}&limit=${limit}`)

  if (!response.ok) {
    throw new Error('Failed to search cities')
  }

  return response.json()
}

export async function getTimezone(lat: number, lon: number): Promise<GeoTimezone> {
  const response = await fetch(`/api/geo/timezone?lat=${lat}&lon=${lon}`)

  if (!response.ok) {
    throw new Error('Failed to get timezone')
  }

  return response.json()
}
