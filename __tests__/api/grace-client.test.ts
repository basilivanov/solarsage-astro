// ############################################################################
// AI_HEADER: MODULE_API_GRACE_CLIENT_TEST — calendar and shared API client tests.
// ROLE: Unit tests for grace-client.ts calendar behavior, preview marker policy and error normalization.
// DEPENDENCIES: vitest, lib/grace/api/client, generated CalendarPayload runtime schema
// GRACE_ANCHORS: [GRACE_CLIENT_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT
// purpose: Validate calendar fetches, preview marker policy and shared API error transformations.
// owns:
//   - __tests__/api/grace-client.test.ts
// inputs: mocked browser fetch responses and a canonical Calendar payload.
// outputs: assertion results.
// dependencies: lib/grace/api/client and the generated CalendarPayload runtime schema.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Calendar success uses a contract-valid payload.
//   - Malformed Calendar response throws ApiContractError with a stable Calendar message.
//   - ApiContractError has status 502 and code SCHEMA_VALIDATION_ERROR.
//   - Error messages do not leak raw payload data or Zod issue details.
//   - Calendar and SSR requests remain marker-free.
// failure_policy: fail test.
// END_MODULE_CONTRACT: M-TEST-API-GRACE-CLIENT

// START_MODULE_MAP: M-TEST-API-GRACE-CLIENT
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - PREVIEW_MARKER_TESTS: pure preview marker authorization and calendar marker boundary.
//   - ERROR_TESTS: shared ApiError and ApiContractError shape.
//   - CALENDAR_TESTS: calendar success, schema failure and HTTP failure.
// owned_tests:
//   - __tests__/api/grace-client.test.ts
// END_MODULE_MAP: M-TEST-API-GRACE-CLIENT

import { describe, it, expect, vi, afterEach } from 'vitest'
import {
  fetchCalendar,
  ApiError,
  ApiContractError,
  shouldEmitTodayPreviewMarker,
} from '../../lib/grace/api/client'
import { CalendarPayloadWireSchema } from '@/packages/contracts/runtime'

const originalFetch = globalThis.fetch

const validCalendarPayload = {
  meta: {
    schemaVersion: 'calendar/v2',
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
      dayState: 'ordinary',
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
describe('Today preview marker policy', () => {
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
  it('builds exact Calendar message when instantiated with Calendar', () => {
    const err = new ApiContractError('Calendar')
    expect(err.name).toBe('ApiContractError')
    expect(err.status).toBe(502)
    expect(err.code).toBe('SCHEMA_VALIDATION_ERROR')
    expect(err.message).toBe('Invalid Calendar payload format from backend')
  })
})

describe('fetchCalendar', () => {
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
