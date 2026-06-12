
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
import { getDayStatus, getMonthStatuses } from '../../lib/api/calendar'

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

  it('normalizes missing dayStatus to even', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => ({}),
    })

    const status = await getDayStatus(new Date('2025-06-15'))
    expect(status).toBe('even')
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
        days: [
          { date: '2025-06-01', dayStatus: 'supportive' },
          { date: '2025-06-02', dayStatus: 'tense' },
          { date: '2025-06-03', dayStatus: 'steady' },
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

  it('throws on error response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
    })

    await expect(getMonthStatuses(2025, 5)).rejects.toThrow('API error 404')
  })
})
