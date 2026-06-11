
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_ACCESS_TEST
// ROLE: Unit tests for access.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for access.test.ts — __tests__/contracts/access.test.ts
// owns:
//   - __tests__/contracts/access.test.ts
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
import { validateAccessInfo, AccessInfoSchema } from '../../lib/contracts/access'

describe('AccessInfoSchema', () => {
  const validAccessInfo = {
    state: 'trial' as const,
    hasAccess: true,
    accessStart: new Date('2026-01-01'),
    accessEnd: new Date('2026-12-31'),
    daysLeft: 30,
  }

  it('validates a complete valid AccessInfo object', () => {
    expect(() => validateAccessInfo(validAccessInfo)).not.toThrow()
    const result = validateAccessInfo(validAccessInfo)
    expect(result.state).toBe('trial')
    expect(result.hasAccess).toBe(true)
    expect(result.daysLeft).toBe(30)
  })

  it('validates AccessInfo with null date boundaries', () => {
    const data = { ...validAccessInfo, accessStart: null, accessEnd: null }
    const result = validateAccessInfo(data)
    expect(result.accessStart).toBeNull()
    expect(result.accessEnd).toBeNull()
  })

  it('rejects AccessInfo with invalid state (not in enum)', () => {
    const data = { ...validAccessInfo, state: 'premium' }
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects AccessInfo with missing hasAccess', () => {
    const { hasAccess, ...data } = validAccessInfo
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects AccessInfo with negative daysLeft', () => {
    const data = { ...validAccessInfo, daysLeft: -1 }
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects AccessInfo with non-integer daysLeft', () => {
    const data = { ...validAccessInfo, daysLeft: 3.5 }
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects AccessInfo with non-date accessStart', () => {
    const data = { ...validAccessInfo, accessStart: '2026-01-01' }
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects AccessInfo with non-boolean hasAccess', () => {
    const data = { ...validAccessInfo, hasAccess: 'yes' }
    expect(() => validateAccessInfo(data)).toThrow()
  })

  it('rejects fully empty object', () => {
    expect(() => validateAccessInfo({})).toThrow()
  })
})
