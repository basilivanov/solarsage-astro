
// ############################################################################
// AI_HEADER: MODULE_API_READINGS_TEST
// ROLE: Unit tests for readings.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// #########################################// START_MODULE_CONTRACT
// purpose: Tests for readingsts behavior
// owns:
//   - __tests__/api/readings.test.ts
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
import { listReadings, getReadingsList } from '../../lib/api/readings'

function mockDayPayload(date: string, locked = false) {
  return {
    ok: true,
    json: async () => ({
      date,
      headline: `Headline for ${date}`,
      dayStatus: 'supportive',
      access: { state: locked ? 'locked' : 'trial' },
      reading: { paragraphs: [`Preview for ${date}`] },
    }),
  }
}

describe('listReadings', () => {
  it('returns catalog with available and coming arrays', () => {
    const catalog = listReadings()
    expect(catalog.available).toBeDefined()
    expect(catalog.coming).toBeDefined()
    expect(Array.isArray(catalog.available)).toBe(true)
    expect(Array.isArray(catalog.coming)).toBe(true)
  })

  it('available includes natal and horary readings', () => {
    const catalog = listReadings()
    const keys = catalog.available.map((r) => r.key)
    expect(keys).toContain('natal')
    expect(keys).toContain('horary')
  })
})

describe('getReadingsList', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns entries for successful fetches', async () => {
    global.fetch = vi.fn().mockResolvedValue(mockDayPayload('2025-06-01'))

    const result = await getReadingsList(1, 0)
    expect(result.entries).toHaveLength(1)
    expect(result.entries[0].date).toBe('2025-06-01')
    expect(result.entries[0].headline).toBe('Headline for 2025-06-01')
  })

  it('skips locked access entries', async () => {
    global.fetch = vi.fn().mockResolvedValue(mockDayPayload('2025-06-01', true))

    const result = await getReadingsList(1, 0)
    expect(result.entries).toHaveLength(0)
  })

  it('returns empty when all fetches fail', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network error'))

    const result = await getReadingsList(3, 0)
    expect(result.entries).toHaveLength(0)
    expect(result.hasMore).toBe(false)
  })

  it('handles mixed success and failure', async () => {
    global.fetch = vi.fn()
      .mockResolvedValueOnce(mockDayPayload('2025-06-01'))
      .mockRejectedValueOnce(new Error('Fail'))
      .mockResolvedValueOnce(mockDayPayload('2025-06-03'))

    const result = await getReadingsList(3, 0)
    expect(result.entries).toHaveLength(2)
  })
})
