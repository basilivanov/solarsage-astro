// ############################################################################
// AI_HEADER: MODULE_API_GRACE_CLIENT_TEST
// ROLE: Unit tests for grace-client.ts (Slice 15)
// DEPENDENCIES: vitest, lib/grace/api/client, e2e/mock-visual/fixtures/day-v2-2026-07-08
// GRACE_ANCHORS: [GRACE_CLIENT_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT
// purpose: Tests for grace-client.ts behavior including preview marker, fetchDay, fetchCalendar, and contract validation errors.
// owns:
//   - __tests__/api/grace-client.test.ts
// inputs: Mocks, fixtures.
// outputs: Assertion results.
// dependencies: lib/grace/api/client.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Success uses contract-valid canonical Today and Calendar payloads.
//   - Malformed Today response throws ApiContractError with Today message.
//   - Malformed Calendar response throws ApiContractError with Calendar message.
//   - ApiContractError has status 502 and code SCHEMA_VALIDATION_ERROR.
//   - Error messages do not leak raw payload data or Zod issue details.
//   - Today marker emission is closed to development loopback port 3003.
//   - Calendar and SSR requests remain marker-free.
// failure_policy: fail test.
// END_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT

// START_MODULE_MAP: M-TEST-API-GRACE-CLIENT
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - PREVIEW_MARKER_TESTS: pure and fetch-boundary marker authorization.
//   - CLIENT_TESTS: validates day and calendar fetches, error transformations, and validation error constraints.
// owned_tests:
//   - __tests__/api/grace-client.test.ts
// END_MODULE_MAP: M-TEST-API-GRACE-CLIENT

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import {
  fetchDay,
  fetchCalendar,
  ApiError,
  ApiContractError,
  shouldEmitTodayPreviewMarker,
  TODAY_PREVIEW_HEADER_NAME,
  TODAY_PREVIEW_HEADER_VALUE,
} from '../../lib/grace/api/client'
import { dayPayloadV2 } from '../../e2e/mock-visual/fixtures/day-v2-2026-07-08'
import { TodayPayloadWireSchema, CalendarPayloadWireSchema } from '@/packages/contracts/runtime'

const originalFetch = globalThis.fetch

const validCalendarPayload = {
  meta: {
    schemaVersion: 'calendar/v1',
    contractVersion: 1,
    generatedAt: '2026-07-24T00:00:00Z',
  },
  month: '2026-07',
  title: 'July 2026',
  allowedRange: {
    from: '2025-07-01',
    to: '2027-07-01',
  },
  days: [
    {
      date: '2026-07-24',
      dayNumber: 24,
      disabled: false,
      isCurrentMonth: true,
      isToday: true,
      dayStatus: 'supportive',
      access: { state: 'full' },
    },
  ],
}

afterEach(() => {
  vi.unstubAllEnvs()
  vi.unstubAllGlobals()
  vi.restoreAllMocks()
  globalThis.fetch = originalFetch
})

// START_BLOCK: PREVIEW_MARKER_TESTS
describe('Today preview marker', () => {
  it('allows development 127.0.0.1:3003', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: '127.0.0.1',
      port: '3003',
    })).toBe(true)
  })

  it('allows development localhost:3003', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: 'localhost',
      port: '3003',
    })).toBe(true)
  })

  it('allows development IPv6 loopback:3003 with or without brackets', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: '[::1]',
      port: '3003',
    })).toBe(true)
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: '::1',
      port: '3003',
    })).toBe(true)
  })

  it('denies local development port 3000', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: '127.0.0.1',
      port: '3000',
    })).toBe(false)
  })

  it('denies a public development hostname on port 3003', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'development',
      hostname: 'preview.example.com',
      port: '3003',
    })).toBe(false)
  })

  it('denies production localhost:3003', () => {
    expect(shouldEmitTodayPreviewMarker({
      nodeEnv: 'production',
      hostname: 'localhost',
      port: '3003',
    })).toBe(false)
  })

  it('keeps SSR fetchDay marker-free', async () => {
    const contractPayload = TodayPayloadWireSchema.parse(dayPayloadV2)
    vi.stubEnv('NODE_ENV', 'development')
    vi.stubGlobal('window', undefined)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => contractPayload,
    }))

    await fetchDay('2026-07-08')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/day/2026-07-08'),
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          Accept: 'application/json',
        }),
      }),
    )
  })

  it('adds the exact marker to browser development loopback:3003 fetchDay', async () => {
    const contractPayload = TodayPayloadWireSchema.parse(dayPayloadV2)
    vi.stubEnv('NODE_ENV', 'development')
    vi.stubGlobal('window', {
      location: { hostname: '127.0.0.1', port: '3003' },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => contractPayload,
    }))

    await fetchDay('2026-07-08')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/day/2026-07-08'),
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          Accept: 'application/json',
          [TODAY_PREVIEW_HEADER_NAME]: TODAY_PREVIEW_HEADER_VALUE,
        }),
      }),
    )
  })

  it('keeps fetchCalendar marker-free in the same local development runtime', async () => {
    const contractPayload = CalendarPayloadWireSchema.parse(validCalendarPayload)
    vi.stubEnv('NODE_ENV', 'development')
    vi.stubGlobal('window', {
      location: { hostname: 'localhost', port: '3003' },
    })
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
      ok: true,
      json: async () => contractPayload,
    }))

    await fetchCalendar('2026-07')

    expect(globalThis.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/calendar?month=2026-07'),
      expect.objectContaining({
        credentials: 'include',
        headers: expect.objectContaining({
          Accept: 'application/json',
        }),
      }),
    )
  })
})
// END_BLOCK: PREVIEW_MARKER_TESTS

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

describe('ApiContractError', () => {
  it('defaults to Today message when instantiated with no args', () => {
    const err = new ApiContractError()
    expect(err.name).toBe('ApiContractError')
    expect(err.status).toBe(502)
    expect(err.code).toBe('SCHEMA_VALIDATION_ERROR')
    expect(err.message).toBe('Invalid Today payload format from backend')
  })

  it('builds exact Calendar message when instantiated with Calendar', () => {
    const err = new ApiContractError('Calendar')
    expect(err.name).toBe('ApiContractError')
    expect(err.status).toBe(502)
    expect(err.code).toBe('SCHEMA_VALIDATION_ERROR')
    expect(err.message).toBe('Invalid Calendar payload format from backend')
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
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/day/2026-07-08'),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('throws ApiContractError on malformed nested V2 response', async () => {
    const sentinel = 'RAW_PAYLOAD_SENTINEL_DO_NOT_LEAK'
    const malformedPayload = {
      ...dayPayloadV2,
      v2: {
        ...dayPayloadV2.v2,
        activationEvidence: [
          {
            technique: 'transit_to_natal',
            techniqueFamily: 'transit',
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
      name: 'ApiContractError',
      status: 502,
      code: 'SCHEMA_VALIDATION_ERROR',
      message: 'Invalid Today payload format from backend',
    })
    await expect(request).rejects.toMatchObject({
      message: expect.not.stringContaining(sentinel),
    })
    await expect(request).rejects.toMatchObject({
      message: expect.not.stringContaining('activationEvidence'),
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

  it('returns contract-valid payload on success and calls real API endpoint', async () => {
    const contractPayload = CalendarPayloadWireSchema.parse(validCalendarPayload)
    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => contractPayload,
    })

    const result = await fetchCalendar('2026-07')
    expect(result).toEqual(contractPayload)
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining('/api/calendar?month=2026-07'),
      expect.objectContaining({ credentials: 'include' }),
    )
  })

  it('throws ApiContractError with Calendar message on malformed 200 response without leaking raw sentinel', async () => {
    const sentinel = 'RAW_CALENDAR_SENTINEL_DO_NOT_LEAK'
    const malformedCalendar = {
      bogusField: sentinel,
    }

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => malformedCalendar,
    })

    const request = fetchCalendar('2026-07')

    await expect(request).rejects.toBeInstanceOf(ApiContractError)
    await expect(request).rejects.toMatchObject({
      name: 'ApiContractError',
      status: 502,
      code: 'SCHEMA_VALIDATION_ERROR',
      message: 'Invalid Calendar payload format from backend',
    })
    await expect(request).rejects.toMatchObject({
      message: expect.not.stringContaining(sentinel),
    })
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
