
// ############################################################################
// AI_HEADER: MODULE_API_CITIES_TEST
// ROLE: Unit tests for cities.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for cities.test.ts — __tests__/api/cities.test.ts
// owns:
//   - __tests__/api/cities.test.ts
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

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getPopularCities, searchCities, searchCitiesAsync } from '../../lib/api/cities'

describe('getPopularCities', () => {
  it('returns array with at least 5 cities', () => {
    const cities = getPopularCities()
    expect(cities.length).toBeGreaterThanOrEqual(5)
  })

  it('each city has lat and lon coordinates', () => {
    const cities = getPopularCities()
    for (const city of cities) {
      expect(typeof city.lat).toBe('number')
      expect(typeof city.lon).toBe('number')
    }
  })

  it('each popular city has timezone', () => {
    const cities = getPopularCities()
    for (const city of cities) {
      expect(city.timezone).toBeDefined()
      expect(typeof city.timezone).toBe('string')
      expect(city.timezone).toContain('/')
    }
  })
})

describe('searchCities', () => {
  it('returns empty array', () => {
    expect(searchCities('Moscow')).toEqual([])
  })
})

describe('searchCitiesAsync', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns empty array on geo error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Geo error'))

    const result = await searchCitiesAsync('Moscow')
    expect(result).toEqual([])
  })

  it('returns cities on successful geo search', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        { id: '1', name: 'Moscow', admin1: null, country: 'RU', lat: 55.75, lon: 37.62, label: 'Moscow' },
      ],
    })

    const result = await searchCitiesAsync('Moscow')
    expect(result).toHaveLength(1)
    expect(result[0].name).toBe('Moscow')
    expect(result[0].lat).toBe(55.75)
    expect(result[0].lon).toBe(37.62)
  })

  it('preserves timezone_id from geo search results', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: '1',
          name: 'Moscow',
          admin1: 'Moscow',
          country: 'Russia',
          lat: 55.75,
          lon: 37.62,
          label: 'Moscow, Moscow, Russia',
          timezone_id: 'Europe/Moscow',
        },
      ],
    })

    const result = await searchCitiesAsync('Moscow')
    expect(result).toHaveLength(1)
    expect(result[0].timezone).toBe('Europe/Moscow')
  })

  it('sets timezone to undefined when timezone_id is null', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: '2',
          name: 'ObscureTown',
          admin1: null,
          country: 'XX',
          lat: 10.0,
          lon: 20.0,
          label: 'ObscureTown, XX',
          timezone_id: null,
        },
      ],
    })

    const result = await searchCitiesAsync('ObscureTown')
    expect(result).toHaveLength(1)
    expect(result[0].timezone).toBeUndefined()
  })

  it('preserves all city fields from geo response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [
        {
          id: '3',
          name: 'Berlin',
          admin1: 'Berlin',
          country: 'Germany',
          lat: 52.52,
          lon: 13.41,
          label: 'Berlin, Germany',
          timezone_id: 'Europe/Berlin',
        },
      ],
    })

    const result = await searchCitiesAsync('Berlin')
    expect(result[0]).toEqual({
      name: 'Berlin',
      country: 'Germany',
      region: 'Berlin',
      lat: 52.52,
      lon: 13.41,
      timezone: 'Europe/Berlin',
    })
  })
})
