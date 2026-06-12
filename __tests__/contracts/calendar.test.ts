
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_CALENDAR_TEST
// ROLE: Unit tests for calendar.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for calendarts behavior
// owns:
//   - __tests__/contracts/calendar.test.ts
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
  validateDayStatus,
  validateDayStatusMap,
  DayStatusSchema,
  DayStatusMapSchema,
} from '../../lib/contracts/calendar'

describe('validateDayStatus', () => {
  it('validates "tense" status', () => {
    expect(() => validateDayStatus('tense')).not.toThrow()
    expect(validateDayStatus('tense')).toBe('tense')
  })

  it('validates "even" status', () => {
    expect(() => validateDayStatus('even')).not.toThrow()
  })

  it('validates "supportive" status', () => {
    expect(() => validateDayStatus('supportive')).not.toThrow()
  })

  it('rejects invalid status string', () => {
    expect(() => validateDayStatus('bad')).toThrow()
  })

  it('rejects non-string input', () => {
    expect(() => validateDayStatus(123)).toThrow()
  })

  it('rejects empty string', () => {
    expect(() => validateDayStatus('')).toThrow()
  })
})

describe('validateDayStatusMap', () => {
  it('validates a correct day status map', () => {
    const map = {
      '2026-06-01': 'tense',
      '2026-06-02': 'even',
      '2026-06-03': 'supportive',
    }
    expect(() => validateDayStatusMap(map)).not.toThrow()
    const result = validateDayStatusMap(map)
    expect(Object.keys(result)).toHaveLength(3)
  })

  it('validates an empty map', () => {
    expect(() => validateDayStatusMap({})).not.toThrow()
  })

  it('rejects map with invalid date key format', () => {
    const map = { '01-06-2026': 'tense' }
    expect(() => validateDayStatusMap(map)).toThrow()
  })

  it('rejects map with invalid status value', () => {
    const map = { '2026-06-01': 'bad' as any }
    expect(() => validateDayStatusMap(map)).toThrow()
  })

  it('rejects non-record input', () => {
    expect(() => validateDayStatusMap('tense')).toThrow()
  })
})
