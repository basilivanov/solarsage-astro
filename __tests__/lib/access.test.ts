import { describe, it, expect } from 'vitest'
import { isDayAccessible } from '../../lib/access'
import type { AccessInfo } from '../../lib/contracts/access'

const start = new Date(2025, 5, 1)
const end = new Date(2025, 5, 7)

function makeInfo(overrides: Partial<AccessInfo> = {}): AccessInfo {
  return {
    state: 'trial',
    hasAccess: true,
    accessStart: start,
    accessEnd: end,
    daysLeft: 7,
    ...overrides,
  }
}

describe('isDayAccessible', () => {
  it('returns true for a day inside the access window', () => {
    expect(isDayAccessible(new Date(2025, 5, 3), makeInfo())).toBe(true)
  })

  it('returns true for the start boundary day', () => {
    expect(isDayAccessible(new Date(2025, 5, 1), makeInfo())).toBe(true)
  })

  it('returns true for the end boundary day', () => {
    expect(isDayAccessible(new Date(2025, 5, 7), makeInfo())).toBe(true)
  })

  it('returns false for a day before the access window', () => {
    expect(isDayAccessible(new Date(2025, 4, 31), makeInfo())).toBe(false)
  })

  it('returns false for a day after the access window', () => {
    expect(isDayAccessible(new Date(2025, 5, 8), makeInfo())).toBe(false)
  })

  it('returns false when hasAccess is false', () => {
    expect(
      isDayAccessible(new Date(2025, 5, 3), makeInfo({ hasAccess: false }))
    ).toBe(false)
  })

  it('returns false when accessStart is null', () => {
    expect(
      isDayAccessible(new Date(2025, 5, 3), makeInfo({ accessStart: null }))
    ).toBe(false)
  })

  it('returns false when accessEnd is null', () => {
    expect(
      isDayAccessible(new Date(2025, 5, 3), makeInfo({ accessEnd: null }))
    ).toBe(false)
  })

  it('returns false for "none" state with no access', () => {
    expect(
      isDayAccessible(
        new Date(2025, 5, 3),
        makeInfo({ state: 'none', hasAccess: false, accessStart: null, accessEnd: null })
      )
    ).toBe(false)
  })
})
