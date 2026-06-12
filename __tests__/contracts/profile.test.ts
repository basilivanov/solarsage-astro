
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_PROFILE_TEST
// ROLE: Unit tests for profile.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for profilets behavior
// owns:
//   - __tests__/contracts/profile.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect } from 'vitest'
import {
  validateProfile,
  safeValidateProfile,
  BirthDatePartsSchema,
  BirthTimePartsSchema,
  ProfileSchema,
} from '../../lib/contracts/profile'

describe('ProfileSchema', () => {
  const validProfile = {
    birthDate: { day: '15', month: '6', year: '1990' },
    birthTime: { hours: '14', minutes: '30', unknown: false },
    birthPlace: 'Moscow',
    currentCity: 'Saint Petersburg',
    birthdayCity: 'Moscow',
    sameAsBirth: false,
    birthdaySameAsCurrent: false,
    gender: 'male',
  }

  it('validates a complete valid Profile', () => {
    expect(() => validateProfile(validProfile)).not.toThrow()
    const result = validateProfile(validProfile)
    expect(result.birthPlace).toBe('Moscow')
    expect(result.birthTime.unknown).toBe(false)
  })

  it('rejects Profile with missing birthDate', () => {
    const { birthDate, ...data } = validProfile
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with invalid birthDate day (non-numeric)', () => {
    const data = { ...validProfile, birthDate: { ...validProfile.birthDate, day: 'XX' } }
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with birthDate year not matching 4-digit regex', () => {
    const data = { ...validProfile, birthDate: { ...validProfile.birthDate, year: '90' } }
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with empty birthPlace', () => {
    const data = { ...validProfile, birthPlace: '' }
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with missing unknown field in birthTime', () => {
    const data = {
      ...validProfile,
      birthTime: { hours: '14', minutes: '30' },
    }
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with empty currentCity', () => {
    const data = { ...validProfile, currentCity: '' }
    expect(() => validateProfile(data)).toThrow()
  })

  it('rejects Profile with non-boolean sameAsBirth', () => {
    const data = { ...validProfile, sameAsBirth: 'yes' }
    expect(() => validateProfile(data)).toThrow()
  })
})

describe('safeValidateProfile', () => {
  it('returns success for valid profile data', () => {
    const valid = {
      birthDate: { day: '1', month: '1', year: '2000' },
      birthTime: { hours: '0', minutes: '0', unknown: true },
      birthPlace: 'City',
      currentCity: 'City',
      birthdayCity: 'City',
      sameAsBirth: true,
      birthdaySameAsCurrent: true,
      gender: 'male',
    }
    const result = safeValidateProfile(valid)
    expect(result.success).toBe(true)
  })

  it('returns error for invalid profile data', () => {
    const result = safeValidateProfile({})
    expect(result.success).toBe(false)
    if (!result.success) {
      expect(result.error.issues.length).toBeGreaterThan(0)
    }
  })
})

describe('BirthDatePartsSchema', () => {
  it('validates correct birth date parts', () => {
    expect(() => BirthDatePartsSchema.parse({ day: '01', month: '12', year: '1985' })).not.toThrow()
  })

  it('rejects day with more than 2 digits', () => {
    expect(() => BirthDatePartsSchema.parse({ day: '123', month: '12', year: '1985' })).toThrow()
  })

  it('rejects year with more than 4 digits', () => {
    expect(() => BirthDatePartsSchema.parse({ day: '01', month: '12', year: '12345' })).toThrow()
  })
})

describe('BirthTimePartsSchema', () => {
  it('validates correct birth time parts', () => {
    expect(() => BirthTimePartsSchema.parse({ hours: '23', minutes: '59', unknown: false })).not.toThrow()
  })

  it('rejects missing hours', () => {
    expect(() => BirthTimePartsSchema.parse({ minutes: '30', unknown: false })).toThrow()
  })
})
