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
})
