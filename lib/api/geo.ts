export interface GeoSuggestion {
  id: string
  name: string
  admin1: string | null
  country: string | null
  lat: number
  lon: number
  label: string
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
