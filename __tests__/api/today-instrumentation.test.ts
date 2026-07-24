// ############################################################################
// AI_HEADER: MODULE_TESTS_TODAY_INSTRUMENTATION
// ROLE: Unit and instrumentation wiring tests for lib/api/today.ts (Slice 13)
// DEPENDENCIES: vitest, lib/api/today, lib/log/instrumented-fetch, e2e/mock-visual/fixtures/day-v2-2026-07-08
// GRACE_ANCHORS: [TODAY_INSTRUMENTATION_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-TODAY-INSTRUMENTATION
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, UTC date formatting, TodayPayload responseContract validator, HTTP error priority, and alias reference equality for getTodayPayload.
// owns:
//   - __tests__/api/today-instrumentation.test.ts
// inputs: mock instrumentedFetch responses and dayPayloadV2 fixture
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-TODAY (getTodayPayload, getTodayPayloadAsync)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-TODAY-INSTRUMENTATION

// START_MODULE_MAP: M-TESTS-TODAY-INSTRUMENTATION
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation, routeTemplate, date URL, init and responseContract
//   - CONTRACT_VALIDATOR_TESTS: test responseContract.validate logic and authoritative parse rejection
//   - ERROR_TESTS: test detail.message and fallback error priority
//   - ALIAS_TESTS: test reference equality of getTodayPayloadAsync
// owned_tests:
//   - __tests__/api/today-instrumentation.test.ts
// END_MODULE_MAP: M-TESTS-TODAY-INSTRUMENTATION

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { getTodayPayload, getTodayPayloadAsync } from "@/lib/api/today"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

describe("getTodayPayload — Slice 13 Instrumentation & Contracts", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches day payload via instrumentedFetch with UTC ISO date string and TodayPayload contract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, dayPayloadV2))

    const testDate = new Date("2026-07-08T15:30:00Z")
    const payload = await getTodayPayload(testDate)

    expect(payload.date).toBe(dayPayloadV2.date)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "today.load",
        routeTemplate: "GET /api/day/{date}",
        url: "/api/day/2026-07-08",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "TodayPayload",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(dayPayloadV2)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("rejects HTTP 200 response with invalid payload shape via authoritative Zod parse", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { invalid: true }))

    const testDate = new Date("2026-07-08T00:00:00Z")
    await expect(getTodayPayload(testDate)).rejects.toThrow()
  })

  it("prioritizes detail.message on HTTP error and falls back to status error string", async () => {
    const testDate = new Date("2026-07-08T00:00:00Z")

    // Priority 1: detail.message
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(500, { detail: { message: "Database connection failed" } })
    )
    await expect(getTodayPayload(testDate)).rejects.toThrow("Database connection failed")

    // Priority 2: Fallback status string
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(500, {}))
    await expect(getTodayPayload(testDate)).rejects.toThrow("API error 500")
  })

  it("preserves reference equality of getTodayPayloadAsync export", () => {
    expect(getTodayPayloadAsync).toBe(getTodayPayload)
  })
})
