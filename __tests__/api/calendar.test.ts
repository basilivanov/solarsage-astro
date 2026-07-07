
// ############################################################################
// AI_HEADER: MODULE_API_CALENDAR_TEST
// ROLE: Unit tests for calendar.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Tests for calendarts behavior
// owns:
//   - __tests__/api/calendar.test.ts
// inputs: Mocks, fixtures
// outputs: Assertion results
// dependencies: local modules
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { getDayStatus, getMonthCalendar, getMonthStatuses } from '../../lib/api/calendar'

const calendarPayload = {
  meta: {
    schemaVersion: 'calendar/v1',
    contractVersion: 1,
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
    dayStatus: 'supportive',
    access: {
      state: 'full',
      reason: 'active_subscription',
      referralDaysLeft: null,
      subscriptionActive: true,
      accessUntil: '2026-05-01',
    },
    lunar: {
      phase: null,
      illumination: null,
      moonSign: null,
      lunarDay: null,
      voidOfCourse: null,
    },
  }],
}

describe('getDayStatus', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns supportive on success response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dayStatus: 'supportive' }),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBe('supportive')
  })

  it('returns tense on success response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dayStatus: 'tense' }),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBe('tense')
  })

  it('normalizes steady to even', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dayStatus: 'steady' }),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBe('even')
  })

  it('returns null when dayStatus is missing', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBeNull()
  })

  it('returns null when dayStatus is invalid', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ dayStatus: 'unknown' }),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBeNull()
  })

  it('throws on error response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
    })

    await expect(getDayStatus(new Date('2025-06-15'))).rejects.toThrow('API error 500')
  })

  it('throws on network error', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

    await expect(getDayStatus(new Date('2025-06-15'))).rejects.toThrow('Network error')
  })
})

describe('getMonthStatuses', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns DayStatusMap on success', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...calendarPayload,
        month: '2025-06',
        days: [
          { ...calendarPayload.days[0], date: '2025-06-01', dayStatus: 'supportive' },
          { ...calendarPayload.days[0], date: '2025-06-02', dayStatus: 'tense' },
          { ...calendarPayload.days[0], date: '2025-06-03', dayStatus: 'steady' },
        ],
      }),
    })

    const map = await getMonthStatuses(2025, 5)
    expect(map).toEqual({
      '2025-06-01': 'supportive',
      '2025-06-02': 'tense',
      '2025-06-03': 'even',
    })
  })

  it('omits days with missing or invalid statuses', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...calendarPayload,
        month: '2025-06',
        days: [
          { ...calendarPayload.days[0], date: '2025-06-01', dayStatus: 'supportive' },
          { ...calendarPayload.days[0], date: '2025-06-02', dayStatus: null },
          { ...calendarPayload.days[0], date: '2025-06-03', dayStatus: undefined },
        ],
      }),
    })

    const map = await getMonthStatuses(2025, 5)
    expect(map).toEqual({
      '2025-06-01': 'supportive',
    })
  })

  it('throws on error response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    })

    await expect(getMonthStatuses(2025, 5)).rejects.toThrow('API error 404')
  })
})

describe('getMonthCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('preserves typed per-day access and lunar read models', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => calendarPayload,
    })

    const result = await getMonthCalendar(2026, 4)
    expect(result.days[0].access?.state).toBe('full')
    expect(result.days[0].lunar?.phase).toBeNull()
    expect(result.days[0].dayStatus).toBe('supportive')
  })

  it('rejects malformed backend calendar payloads', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({
        ...calendarPayload,
        days: [{ ...calendarPayload.days[0], dayStatus: 'even' }],
      }),
    })

    await expect(getMonthCalendar(2026, 4)).rejects.toThrow()
  })
})
