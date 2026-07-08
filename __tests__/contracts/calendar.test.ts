
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
  validateCalendarPayloadReadModel,
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
    const map = { '2026-06-01': 'bad' }
    expect(() => validateDayStatusMap(map)).toThrow()
  })

  it('rejects non-record input', () => {
    expect(() => validateDayStatusMap('tense')).toThrow()
  })
})

describe('validateCalendarPayloadReadModel', () => {
  const payload = {
    meta: {
      schemaVersion: 'calendar/v1',
      contractVersion: 2,
      generatedAt: '2026-05-01T00:00:00Z',
    },
    month: '2026-05',
    title: 'May 2026',
    allowedRange: { from: '2024-01-01', to: '2028-12-31' },
    days: [{
      date: '2026-05-01',
      dayNumber: 1,
      isCurrentMonth: true,
      isToday: false,
      disabled: false,
      dayStatus: 'steady' as const,
      access: {
        state: 'full' as const,
        reason: 'active_subscription' as const,
        referralDaysLeft: null,
        subscriptionActive: true,
        accessUntil: '2026-05-01',
      },
      lunar: {
        phase: 'waning_crescent',
        phaseIndex: 7,
        phaseLabel: 'убыв. серп',
        illumination: 39,
        moonSign: 'Cancer',
        moonSignLabel: 'Рак',
        lunarDay: 24,
        voidOfCourse: false,
      },
    }],
  }

  it('validates full backend calendar payload with access and lunar fields', () => {
    const result = validateCalendarPayloadReadModel(payload)
    expect(result.days[0].dayStatus).toBe('steady')
    expect(result.days[0].access?.state).toBe('full')
    expect(result.days[0].lunar.phase).toBe('waning_crescent')
    expect(result.days[0].lunar.phaseIndex).toBe(7)
    expect(result.days[0].lunar.phaseLabel).toBe('убыв. серп')
    expect(result.days[0].lunar.moonSign).toBe('Cancer')
    expect(result.days[0].lunar.moonSignLabel).toBe('Рак')
    expect(result.days[0].lunar.voidOfCourse).toBe(false)
  })

  it('preserves null as unknown for optional lunar facts', () => {
    const result = validateCalendarPayloadReadModel({
      ...payload,
      days: [{
        ...payload.days[0],
        lunar: {
          phase: null,
          phaseIndex: null,
          phaseLabel: null,
          illumination: null,
          moonSign: null,
          moonSignLabel: null,
          lunarDay: null,
          voidOfCourse: null,
        },
      }],
    })

    expect(result.days[0].lunar.voidOfCourse).toBeNull()
  })

  it('rejects lunar phase indexes outside the stable 0..7 range', () => {
    const data = {
      ...payload,
      days: [{
        ...payload.days[0],
        lunar: {
          ...payload.days[0].lunar,
          phaseIndex: 8,
        },
      }],
    }

    expect(() => validateCalendarPayloadReadModel(data)).toThrow()
  })

  it('rejects the legacy UI-only "even" status in backend read models', () => {
    const data = {
      ...payload,
      days: [{ ...payload.days[0], dayStatus: 'even' }],
    }
    expect(() => validateCalendarPayloadReadModel(data)).toThrow()
  })

  it('rejects incomplete backend calendar payloads', () => {
    const { meta, ...incomplete } = payload
    expect(() => validateCalendarPayloadReadModel(incomplete)).toThrow()
  })
})
