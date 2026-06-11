
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CITY_TEST
// ROLE: Unit tests for city.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for city.test.ts — __tests__/contracts/city.test.ts
// owns:
//   - __tests__/contracts/city.test.ts
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

import { describe, it, expect } from 'vitest'
import { formatCity, validateCity, validateCities, CitySchema } from '../../lib/contracts/city'

const validCity = {
  name: 'Moscow',
  country: 'Russia',
  region: 'Central',
  lat: 55.7558,
  lon: 37.6173,
  timezone: 'Europe/Moscow',
}

describe('validateCity', () => {
  it('validates a complete city object', () => {
    expect(() => validateCity(validCity)).not.toThrow()
    const result = validateCity(validCity)
    expect(result.name).toBe('Moscow')
    expect(result.country).toBe('Russia')
  })

  it('validates a minimal city with only name and country', () => {
    const minimal = { name: 'Paris', country: 'France' }
    expect(() => validateCity(minimal)).not.toThrow()
  })

  it('rejects city with empty name', () => {
    const city = { name: '', country: 'Russia' }
    expect(() => validateCity(city)).toThrow()
  })

  it('rejects city with empty country', () => {
    const city = { name: 'Moscow', country: '' }
    expect(() => validateCity(city)).toThrow()
  })

  it('rejects city with missing name', () => {
    expect(() => validateCity({ country: 'Russia', lat: 55 })).toThrow()
  })

  it('rejects city with missing country', () => {
    expect(() => validateCity({ name: 'Moscow', lat: 55 })).toThrow()
  })
})

describe('validateCities', () => {
  it('validates a correct array of cities', () => {
    const cities = [
      { name: 'Moscow', country: 'Russia' },
      { name: 'Paris', country: 'France' },
    ]
    expect(() => validateCities(cities)).not.toThrow()
    const result = validateCities(cities)
    expect(result).toHaveLength(2)
  })

  it('rejects array with an invalid city', () => {
    const cities = [
      { name: 'Moscow', country: 'Russia' },
      { name: '', country: 'France' },
    ]
    expect(() => validateCities(cities)).toThrow()
  })

  it('rejects non-array input', () => {
    expect(() => validateCities({ name: 'Moscow', country: 'Russia' })).toThrow()
  })
})

describe('formatCity', () => {
  it('formats a City object as "Name, Country"', () => {
    expect(formatCity({ name: 'Moscow', country: 'Russia' })).toBe('Moscow, Russia')
  })

  it('returns the string itself when given a string', () => {
    expect(formatCity('Moscow, Russia')).toBe('Moscow, Russia')
  })
})
