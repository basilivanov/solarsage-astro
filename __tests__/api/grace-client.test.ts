
// ############################################################################
// AI_HEADER: MODULE_API_GRACE_CLIENT_TEST
// ROLE: Unit tests for grace-client.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for grace-client.test.ts — __tests__/api/grace-client.test.ts
// owns:
//   - __tests__/api/grace-client.test.ts
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

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchDay, fetchCalendar, ApiError } from '../../lib/grace/api/client'

describe('ApiError', () => {
  it('has correct name and extends Error', () => {
    const err = new ApiError('test message', 400)
    expect(err.name).toBe('ApiError')
    expect(err).toBeInstanceOf(Error)
    expect(err).toBeInstanceOf(ApiError)
  })

  it('stores status and code', () => {
    const err = new ApiError('test', 422, 'NOT_ONBOARDED')
    expect(err.status).toBe(422)
    expect(err.code).toBe('NOT_ONBOARDED')
    expect(err.message).toBe('test')
  })
})

describe('fetchDay', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns payload on success', async () => {
    const payload = { date: '2025-06-01', headline: 'Test', dayStatus: 'supportive' as const }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    const result = await fetchDay('2025-06-01')
    expect(result).toEqual(payload)
  })

  it('throws ApiError on 404', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 404,
      statusText: 'Not Found',
      json: async () => ({ detail: 'Day not found' }),
    })

    try {
      await fetchDay('2025-06-01')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(404)
      expect((err as ApiError).message).toBe('Day not found')
    }
  })

  it('throws ApiError with code on 422 NOT_ONBOARDED', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 422,
      statusText: 'Unprocessable Entity',
      json: async () => ({
        detail: { message: 'User not onboarded', code: 'NOT_ONBOARDED' },
      }),
    })

    try {
      await fetchDay('2025-06-01')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(422)
      expect((err as ApiError).code).toBe('NOT_ONBOARDED')
      expect((err as ApiError).message).toBe('User not onboarded')
    }
  })

  it('throws ApiError on 401 unauthorized', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 401,
      statusText: 'Unauthorized',
      json: async () => ({ detail: 'Unauthorized' }),
    })

    try {
      await fetchDay('2025-06-01')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).status).toBe(401)
    }
  })

  it('throws on network fetch rejection', async () => {
    global.fetch = vi.fn().mockRejectedValue(new Error('Network failure'))

    await expect(fetchDay('2025-06-01')).rejects.toThrow('Network failure')
  })

  it('uses statusText when JSON parsing fails', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Internal Server Error',
      json: async () => {
        throw new Error('Not JSON')
      },
    })

    try {
      await fetchDay('2025-06-01')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toBe('Internal Server Error')
      expect((err as ApiError).status).toBe(500)
    }
  })
})

describe('fetchCalendar', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('returns payload on success', async () => {
    const payload = { days: [{ date: '2025-06-01', dayStatus: 'supportive' }] }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    const result = await fetchCalendar('2025-06')
    expect(result).toEqual(payload)
  })

  it('throws ApiError on error response', async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: 'Error',
      json: async () => ({ detail: 'Server error' }),
    })

    try {
      await fetchCalendar('2025-06')
      expect.fail('Should have thrown')
    } catch (err) {
      expect(err).toBeInstanceOf(ApiError)
      expect((err as ApiError).message).toBe('Server error')
    }
  })
})
