
// ############################################################################
// AI_HEADER: MODULE_API_GRACE_CLIENT_TEST
// ROLE: Unit tests for grace-client.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT
// purpose: Tests for grace-client.ts behavior.
// owns:
//   - __tests__/api/grace-client.test.ts
// inputs: Mocks, fixtures.
// outputs: Assertion results.
// dependencies: lib/grace/api/client.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Success uses contract-valid canonical Today payload.
//   - Malformed nested V2 response throws ApiContractError.
//   - ApiContractError has status 502 and code SCHEMA_VALIDATION_ERROR.
//   - Error messages do not leak raw payload data or Zod issue details.
// failure_policy: fail test.
// END_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT

// START_MODULE_MAP: M-TEST-API-GRACE-CLIENT
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - CLIENT_TESTS: validates day and calendar fetches, error transformations, and validation error constraints.
// owned_tests:
//   - __tests__/api/grace-client.test.ts
// END_MODULE_MAP: M-TEST-API-GRACE-CLIENT

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { fetchDay, fetchCalendar, ApiError, ApiContractError } from '../../lib/grace/api/client'
import { dayPayloadV2 } from '../../e2e/mock-visual/fixtures/day-v2-2026-07-08'
import { TodayPayloadWireSchema } from '@/packages/contracts/runtime'

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

  it('returns payload on success and calls real API endpoint (not demo data)', async () => {
    const contractPayload = TodayPayloadWireSchema.parse(dayPayloadV2)

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => contractPayload,
    })

    const result = await fetchDay('2026-07-08')
    expect(result).toEqual(contractPayload)
    // Verify it calls the real /api/day endpoint, not returning demo data
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/day/2026-07-08'),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('throws ApiContractError on malformed nested V2 response', async () => {
    const sentinel = "RAW_PAYLOAD_SENTINEL_DO_NOT_LEAK"
    const malformedPayload = {
      ...dayPayloadV2,
      v2: {
        ...dayPayloadV2.v2,
        activationEvidence: [
          {
            // Missing required id field to trigger validation error
            technique: "transit_to_natal",
            techniqueFamily: "transit",
            evidence: sentinel,
          },
        ],
      },
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => malformedPayload,
    })

    const request = fetchDay('2026-07-08')

    await expect(request).rejects.toBeInstanceOf(ApiContractError)
    await expect(request).rejects.toMatchObject({
      name: "ApiContractError",
      status: 502,
      code: "SCHEMA_VALIDATION_ERROR",
      message: "Invalid Today payload format from backend",
    })
    await expect(request).rejects.toMatchObject({
      message: expect.not.stringContaining(sentinel),
    })
    await expect(request).rejects.toMatchObject({
      message: expect.not.stringContaining("activationEvidence"),
    })
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

  it('returns payload on success and calls real API endpoint (not demo data)', async () => {
    const payload = { days: [{ date: '2025-06-01', dayStatus: 'supportive' }] }
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => payload,
    })

    const result = await fetchCalendar('2025-06')
    expect(result).toEqual(payload)
    // Verify it calls the real /api/calendar endpoint, not returning demo data
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/calendar?month=2025-06'),
      expect.objectContaining({ credentials: 'include' }),
    )
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
