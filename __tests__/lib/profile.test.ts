
// ############################################################################
// AI_HEADER: MODULE_LIB_PROFILE_TEST
// ROLE: Unit tests for profile.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for profilets behavior
// owns:
//   - __tests__/lib/profile.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi } from 'vitest'
import {
  apiProfileToProfile,
  EMPTY_PROFILE,
  formatBirthDate,
  formatBirthTime,
  isValidBirthDate,
  isValidBirthTime,
  loadProfile,
  profileToApiWrite,
  saveProfile,
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
  it('saveProfile marks cached profiles as API-sourced', () => {
    const store: Record<string, string> = {}
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    saveProfile(EMPTY_PROFILE)

    expect(store['lumen:profile']).toBeDefined()
    expect(JSON.parse(store['lumen:profile'])).toEqual({
      source: 'api',
      profile: EMPTY_PROFILE,
    })
  })

  it('loadProfile returns EMPTY_PROFILE when localStorage is empty', () => {
    const store: Record<string, string> = {}
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    const result = loadProfile()

    expect(result).toEqual(EMPTY_PROFILE)
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

    expect(result).toEqual(EMPTY_PROFILE)
  })

  it('loadProfile ignores legacy unmarked profile data', () => {
    const store: Record<string, string> = {
      'lumen:profile': JSON.stringify({ birthPlace: 'Москва, Россия' }),
    }
    const mockLocalStorage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => { store[key] = value },
      removeItem: (key: string) => { delete store[key] },
    }
    vi.stubGlobal('window', { localStorage: mockLocalStorage })

    const result = loadProfile()

    expect(result).toEqual(EMPTY_PROFILE)
  })

  it('loadProfile restores a marked API profile', () => {
    const cached = {
      ...EMPTY_PROFILE,
      birthPlace: 'Москва, Россия',
      birthLocation: {
        city: 'Москва, Россия',
        lat: 55.7558,
        lon: 37.6173,
        timezone: 'Europe/Moscow',
      },
    }
    const store: Record<string, string> = {
      'lumen:profile': JSON.stringify({ source: 'api', profile: cached }),
    }
    vi.stubGlobal('window', {
      localStorage: {
        getItem: (key: string) => store[key] ?? null,
        setItem: (key: string, value: string) => { store[key] = value },
        removeItem: (key: string) => { delete store[key] },
      },
    })

    expect(loadProfile()).toEqual(cached)
  })
})

describe('profile API mapping', () => {
  const apiProfile = {
    userId: '64c31e3a-a7db-4a35-b12a-cd75fc8156d6',
    firstName: 'Ada',
    gender: 'female' as const,
    isOnboarded: true,
    birth: {
      birthday: '1985-12-10',
      birthTime: '12:05:00',
      birthCity: 'London, UK',
      birthLat: 51.5074,
      birthLon: -0.1278,
      birthTz: 'Europe/London',
    },
    currentLocation: {
      city: 'Lisbon, Portugal',
      lat: 38.7223,
      lon: -9.1393,
      tz: 'Europe/Lisbon',
    },
    birthdayLocation: {
      city: 'Tokyo, Japan',
      lat: 35.6762,
      lon: 139.6503,
      tz: 'Asia/Tokyo',
    },
  }

  it('maps backend profile fields and location metadata into the UI model', () => {
    const profile = apiProfileToProfile(apiProfile)

    expect(profile.firstName).toBe('Ada')
    expect(profile.gender).toBe('female')
    expect(profile.birthDate).toEqual({ day: '10', month: '12', year: '1985' })
    expect(profile.birthTime).toEqual({ hours: '12', minutes: '05', unknown: false })
    expect(profile.birthLocation).toEqual({
      city: 'London, UK',
      lat: 51.5074,
      lon: -0.1278,
      timezone: 'Europe/London',
    })
    expect(profile.currentLocation?.timezone).toBe('Europe/Lisbon')
    expect(profile.birthdayLocation?.timezone).toBe('Asia/Tokyo')
  })

  it('maps an empty backend profile to EMPTY_PROFILE', () => {
    expect(apiProfileToProfile({
      ...apiProfile,
      firstName: null,
      gender: null,
      isOnboarded: false,
      birth: {},
      currentLocation: null,
      birthdayLocation: null,
    })).toEqual(EMPTY_PROFILE)
  })

  it('serializes the full profile without dropping coordinates or timezones', () => {
    expect(profileToApiWrite(apiProfileToProfile(apiProfile))).toEqual({
      firstName: 'Ada',
      gender: 'female',
      birth: {
        birthday: '1985-12-10',
        birthTime: '12:05:00',
        birthCity: 'London, UK',
        birthLat: 51.5074,
        birthLon: -0.1278,
        birthTz: 'Europe/London',
      },
      currentLocation: {
        city: 'Lisbon, Portugal',
        lat: 38.7223,
        lon: -9.1393,
        tz: 'Europe/Lisbon',
      },
      birthdayLocation: {
        city: 'Tokyo, Japan',
        lat: 35.6762,
        lon: 139.6503,
        tz: 'Asia/Tokyo',
      },
    })
  })

  it('serializes empty UI profile without synthetic nullable locations', () => {
    expect(profileToApiWrite(EMPTY_PROFILE)).toEqual({
      firstName: null,
      gender: null,
      birth: {
        birthday: null,
        birthTime: null,
        birthCity: null,
        birthLat: null,
        birthLon: null,
        birthTz: null,
      },
      currentLocation: null,
      birthdayLocation: null,
    })
  })
})
