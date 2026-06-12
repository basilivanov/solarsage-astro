
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY_TEST
// ROLE: Unit tests for today.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for todayts behavior
// owns:
//   - __tests__/contracts/today.test.ts
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
import { validateAdaptedTodayPayload, TodayPayloadSchema } from '../../lib/contracts/today'

const validTodayPayload = {
  date: '2026-06-01',
  notes: [
    {
      id: 'note-1',
      iconName: 'moon',
      title: 'Lunar phase',
      description: 'Waxing gibbous',
      hint: {
        meaning: 'Growth phase',
        whyImportant: 'Affects emotions',
        howForMe: 'Channel your energy',
      },
    },
  ],
  reading: {
    paragraphs: ['First paragraph.', 'Second paragraph.'],
  },
  why: [
    {
      id: 'why-1',
      iconName: 'compass',
      title: 'Direction',
      paragraphs: ['Analysis paragraph one.', 'Analysis paragraph two.'],
      bullets: ['bullet 1', 'bullet 2'],
    },
  ],
  keyInsight: 'Today is a day of transformation.',
}

describe('validateAdaptedTodayPayload', () => {
  it('validates a complete valid TodayPayload', () => {
    expect(() => validateAdaptedTodayPayload(validTodayPayload)).not.toThrow()
    const result = validateAdaptedTodayPayload(validTodayPayload)
    expect(result.date).toBe('2026-06-01')
    expect(result.notes).toHaveLength(1)
    expect(result.keyInsight).toBe('Today is a day of transformation.')
  })

  it('rejects payload with invalid date format (dd-mm-yyyy)', () => {
    const data = { ...validTodayPayload, date: '01-06-2026' }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects payload with date missing dashes', () => {
    const data = { ...validTodayPayload, date: '20260601' }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects payload with missing keyInsight', () => {
    const { keyInsight, ...data } = validTodayPayload
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects payload with empty keyInsight', () => {
    const data = { ...validTodayPayload, keyInsight: '' }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects payload with missing reading', () => {
    const { reading, ...data } = validTodayPayload
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects payload with empty paragraphs in reading', () => {
    const data = { ...validTodayPayload, reading: { paragraphs: [] } }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects note with missing hint', () => {
    const data = {
      ...validTodayPayload,
      notes: [{ id: 'n1', iconName: 'moon', title: 'Test', description: 'Test' }],
    }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects note with empty hint fields', () => {
    const data = {
      ...validTodayPayload,
      notes: [
        {
          id: 'n1',
          iconName: 'moon',
          title: 'Test',
          description: 'Test',
          hint: { meaning: '', whyImportant: 'x', howForMe: 'x' },
        },
      ],
    }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects why section with empty paragraphs array', () => {
    const data = {
      ...validTodayPayload,
      why: [
        {
          id: 'w1',
          iconName: 'compass',
          title: 'Direction',
          paragraphs: [],
        },
      ],
    }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects why section with missing title', () => {
    const data = {
      ...validTodayPayload,
      why: [
        {
          id: 'w1',
          iconName: 'compass',
          paragraphs: ['Text'],
        },
      ],
    }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })

  it('rejects why section with empty id', () => {
    const data = {
      ...validTodayPayload,
      why: [{ ...validTodayPayload.why[0], id: '' }],
    }
    expect(() => validateAdaptedTodayPayload(data)).toThrow()
  })
})
