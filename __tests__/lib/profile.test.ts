
// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE_TEST
// ROLE: Unit tests for profile.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for profile.test.ts — __tests__/lib/profile.test.ts
// owns:
//   - __tests__/lib/profile.test.ts
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

import { describe, it, expect, vi } from 'vitest'
import {
  formatBirthDate,
  formatBirthTime,
  isValidBirthDate,
  isValidBirthTime,
  loadProfile,
  saveProfile,
  DEFAULT_PROFILE,
  type BirthDateParts,
  type BirthTimeParts,
} from '../../lib/profile'

describe('formatBirthDate', () => {
  it('formats a valid date as "14 июля 1995"', () => {
    const date: BirthDateParts = { day: '14', month: '07', year: '1995' }
    expect(formatBirthDate(date)).toBe('14 июля 1995')
  })

  it('formats a single-digit day without leading zero in output', () => {
    const date: BirthDateParts = { day: '1', month: '01', year: '2020' }
    expect(formatBirthDate(date)).toBe('1 января 2020')
  })

  it('returns "Не указано" when day is not a number', () => {
    const date: BirthDateParts = { day: 'xx', month: '07', year: '1995' }
    expect(formatBirthDate(date)).toBe('Не указано')
  })

  it('returns "Не указано" when month is out of range (13)', () => {
    const date: BirthDateParts = { day: '14', month: '13', year: '1995' }
    expect(formatBirthDate(date)).toBe('Не указано')
  })

  it('returns "Не указано" when month is 0', () => {
    const date: BirthDateParts = { day: '14', month: '0', year: '1995' }
    expect(formatBirthDate(date)).toBe('Не указано')
  })

  it('returns "Не указано" when year is NaN', () => {
    const date: BirthDateParts = { day: '14', month: '07', year: 'abcd' }
    expect(formatBirthDate(date)).toBe('Не указано')
  })

  it('formats December correctly', () => {
    const date: BirthDateParts = { day: '31', month: '12', year: '2025' }
    expect(formatBirthDate(date)).toBe('31 декабря 2025')
  })
})

describe('formatBirthTime', () => {
  it('formats a valid time as "08:42"', () => {
    const time: BirthTimeParts = { hours: '08', minutes: '42', unknown: false }
    expect(formatBirthTime(time)).toBe('08:42')
  })

  it('formats single-digit hours and minutes with padding', () => {
    const time: BirthTimeParts = { hours: '8', minutes: '5', unknown: false }
    expect(formatBirthTime(time)).toBe('08:05')
  })

  it('returns "Не знаю" when unknown is true', () => {
    const time: BirthTimeParts = { hours: '00', minutes: '00', unknown: true }
    expect(formatBirthTime(time)).toBe('Не знаю')
  })

  it('returns "Не указано" when hours is not numeric', () => {
    const time: BirthTimeParts = { hours: 'ab', minutes: '42', unknown: false }
    expect(formatBirthTime(time)).toBe('Не указано')
  })

  it('returns "Не указано" when minutes is not numeric', () => {
    const time: BirthTimeParts = { hours: '08', minutes: 'xy', unknown: false }
    expect(formatBirthTime(time)).toBe('Не указано')
  })
})

describe('isValidBirthDate', () => {
  it('returns true for a valid birth date', () => {
    const date: BirthDateParts = { day: '14', month: '07', year: '1995' }
    expect(isValidBirthDate(date)).toBe(true)
  })

  it('returns false when day is out of range (32)', () => {
    const date: BirthDateParts = { day: '32', month: '07', year: '1995' }
    expect(isValidBirthDate(date)).toBe(false)
  })

  it('returns false when day is 0', () => {
    const date: BirthDateParts = { day: '0', month: '07', year: '1995' }
    expect(isValidBirthDate(date)).toBe(false)
  })

  it('returns false when month is out of range (13)', () => {
    const date: BirthDateParts = { day: '14', month: '13', year: '1995' }
    expect(isValidBirthDate(date)).toBe(false)
  })

  it('returns false when year has wrong digit count', () => {
    const date: BirthDateParts = { day: '14', month: '07', year: '95' }
    expect(isValidBirthDate(date)).toBe(false)
  })

  it('returns false when year is before 1900', () => {
    const date: BirthDateParts = { day: '14', month: '07', year: '1899' }
    expect(isValidBirthDate(date)).toBe(false)
  })

  it('returns false when day contains non-digit chars', () => {
    const date: BirthDateParts = { day: '1a', month: '07', year: '1995' }
    expect(isValidBirthDate(date)).toBe(false)
  })
})

describe('isValidBirthTime', () => {
  it('returns true for a valid time', () => {
    const time: BirthTimeParts = { hours: '14', minutes: '30', unknown: false }
    expect(isValidBirthTime(time)).toBe(true)
  })

  it('returns true when time is unknown', () => {
    const time: BirthTimeParts = { hours: '', minutes: '', unknown: true }
    expect(isValidBirthTime(time)).toBe(true)
  })

  it('returns false when hours is out of range (24)', () => {
    const time: BirthTimeParts = { hours: '24', minutes: '00', unknown: false }
    expect(isValidBirthTime(time)).toBe(false)
  })

  it('returns false when minutes is out of range (60)', () => {
    const time: BirthTimeParts = { hours: '12', minutes: '60', unknown: false }
    expect(isValidBirthTime(time)).toBe(false)
  })

  it('returns false when hours is negative', () => {
    const time: BirthTimeParts = { hours: '-1', minutes: '00', unknown: false }
    expect(isValidBirthTime(time)).toBe(false)
  })

  it('returns false when hours contains non-digit chars', () => {
    const time: BirthTimeParts = { hours: '1a', minutes: '00', unknown: false }
    expect(isValidBirthTime(time)).toBe(false)
  })
})

describe('loadProfile and saveProfile', () => {
  it('saveProfile stores profile JSON in localStorage', () => {
    const store: Record<string, string> = {}
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    saveProfile(DEFAULT_PROFILE)

    expect(store['lumen:profile']).toBeDefined()
    expect(JSON.parse(store['lumen:profile']).birthPlace).toBe('Киев, Украина')
  })

  it('loadProfile returns DEFAULT_PROFILE when localStorage is empty', () => {
    const store: Record<string, string> = {}
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    const result = loadProfile()

    expect(result.birthDate.day).toBe('14')
    expect(result.birthDate.month).toBe('07')
    expect(result.birthDate.year).toBe('1995')
    expect(result.birthTime.hours).toBe('08')
    expect(result.birthTime.minutes).toBe('42')
    expect(result.birthTime.unknown).toBe(false)
  })

  it('loadProfile returns DEFAULT_PROFILE when stored JSON is corrupted', () => {
    const store: Record<string, string> = { 'lumen:profile': '{bad json' }
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    const result = loadProfile()

    expect(result.birthDate.day).toBe('14')
    expect(result.birthTime.unknown).toBe(false)
  })

  it('loadProfile merges stored data with DEFAULT_PROFILE', () => {
    const store: Record<string, string> = {
      'lumen:profile': JSON.stringify({
        birthPlace: 'Москва, Россия',
        birthDate: { day: '22' },
      }),
    }
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    const result = loadProfile()

    expect(result.birthPlace).toBe('Москва, Россия')
    expect(result.birthDate.day).toBe('22')
    expect(result.birthDate.month).toBe('07')
  })
})
