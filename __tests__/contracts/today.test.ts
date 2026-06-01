import { describe, it, expect } from 'vitest'
import { validateTodayPayload, TodayPayloadSchema } from '../../lib/contracts/today'

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

describe('validateTodayPayload', () => {
  it('validates a complete valid TodayPayload', () => {
    expect(() => validateTodayPayload(validTodayPayload)).not.toThrow()
    const result = validateTodayPayload(validTodayPayload)
    expect(result.date).toBe('2026-06-01')
    expect(result.notes).toHaveLength(1)
    expect(result.keyInsight).toBe('Today is a day of transformation.')
  })

  it('rejects payload with invalid date format (dd-mm-yyyy)', () => {
    const data = { ...validTodayPayload, date: '01-06-2026' }
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects payload with date missing dashes', () => {
    const data = { ...validTodayPayload, date: '20260601' }
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects payload with missing keyInsight', () => {
    const { keyInsight, ...data } = validTodayPayload
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects payload with empty keyInsight', () => {
    const data = { ...validTodayPayload, keyInsight: '' }
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects payload with missing reading', () => {
    const { reading, ...data } = validTodayPayload
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects payload with empty paragraphs in reading', () => {
    const data = { ...validTodayPayload, reading: { paragraphs: [] } }
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects note with missing hint', () => {
    const data = {
      ...validTodayPayload,
      notes: [{ id: 'n1', iconName: 'moon', title: 'Test', description: 'Test' }],
    }
    expect(() => validateTodayPayload(data)).toThrow()
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
    expect(() => validateTodayPayload(data)).toThrow()
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
    expect(() => validateTodayPayload(data)).toThrow()
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
    expect(() => validateTodayPayload(data)).toThrow()
  })

  it('rejects why section with empty id', () => {
    const data = {
      ...validTodayPayload,
      why: [{ ...validTodayPayload.why[0], id: '' }],
    }
    expect(() => validateTodayPayload(data)).toThrow()
  })
})
