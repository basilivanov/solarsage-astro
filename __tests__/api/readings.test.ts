// ############################################################################
// AI_HEADER: MODULE_API_READINGS_TEST
// ROLE: Unit tests for lib/api/readings.ts (Slice 07)
// DEPENDENCIES: vitest, lib/api/readings, lib/log/instrumented-fetch, e2e/mock-visual/fixtures/day-v2-2026-07-08
// GRACE_ANCHORS: [READINGS_INSTRUMENTATION_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-READINGS
// purpose: Validate past-day readings aggregation, instrumentedFetch call wiring, static route templates, TodayPayload contract validation, and per-day fail-soft handling.
// owns:
//   - __tests__/api/readings.test.ts
// inputs: mock instrumentedFetch responses and dayPayloadV2 fixture
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-READINGS (getReadingsList, listReadings)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-READINGS

// START_MODULE_MAP: M-TESTS-READINGS
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - CATALOG_TESTS: test static listReadings catalog output
//   - HISTORY_INSTRUMENTATION_TESTS: test instrumentedFetch operation, routeTemplate, responseContract, and per-day fail-soft aggregation
// owned_tests:
//   - __tests__/api/readings.test.ts
// END_MODULE_MAP: M-TESTS-READINGS

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { listReadings, getReadingsList } from "@/lib/api/readings"

function mockDayPayloadResponse(date: string, locked = false) {
  return new Response(
    JSON.stringify({
      ...dayPayloadV2,
      date,
      access: { ...dayPayloadV2.access, state: locked ? "locked" : "trial" },
      headline: `Headline for ${date}`,
      reading: { ...dayPayloadV2.reading, paragraphs: [`Preview for ${date}`] },
    }),
    { status: 200 }
  )
}

describe("listReadings Catalog", () => {
  it("returns catalog with available and coming arrays", () => {
    const catalog = listReadings()
    expect(catalog.available).toBeDefined()
    expect(catalog.coming).toBeDefined()
    expect(Array.isArray(catalog.available)).toBe(true)
    expect(Array.isArray(catalog.coming)).toBe(true)
  })

  it("available includes natal and horary readings", () => {
    const catalog = listReadings()
    expect(catalog.available.map((r) => r.key)).toContain("natal")
    expect(catalog.available.map((r) => r.key)).toContain("horary")
  })
})

describe("getReadingsList — Slice 07 Instrumentation", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("calls instrumentedFetch with static routeTemplate GET /api/day/{date} and actual date URL separately", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayPayloadResponse("2026-07-23"))

    const result = await getReadingsList(1, 0)
    expect(result.entries).toHaveLength(1)
    expect(result.entries[0].date).toBe("2026-07-23")

    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "readings.day_history",
        routeTemplate: "GET /api/day/{date}",
        url: expect.stringMatching(/\/api\/day\/\d{4}-\d{2}-\d{2}$/),
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

    // Ensure date was NOT placed into routeTemplate or operation
    const firstCallOption = mockInstrumentedFetch.mock.calls[0][0]
    expect(firstCallOption.routeTemplate).toBe("GET /api/day/{date}")
    expect(firstCallOption.operation).toBe("readings.day_history")
  })

  it("makes 3 instrumentedFetch calls with the exact same routeTemplate on limit=3", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(mockDayPayloadResponse("2026-07-23"))
      .mockResolvedValueOnce(mockDayPayloadResponse("2026-07-22"))
      .mockResolvedValueOnce(mockDayPayloadResponse("2026-07-21"))

    const result = await getReadingsList(3, 0)
    expect(result.entries).toHaveLength(3)

    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(3)
    mockInstrumentedFetch.mock.calls.forEach((call) => {
      expect(call[0].routeTemplate).toBe("GET /api/day/{date}")
      expect(call[0].operation).toBe("readings.day_history")
    })
  })

  it("responseContract accepts canonical dayPayloadV2 fixture and rejects empty object", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayPayloadResponse("2026-07-23"))

    await getReadingsList(1, 0)

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract).toBeDefined()
    expect(contract.validate(dayPayloadV2)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("skips locked access entries", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayPayloadResponse("2026-07-23", true))

    const result = await getReadingsList(1, 0)
    expect(result.entries).toHaveLength(0)
  })

  it("returns empty when all fetches fail or reject", async () => {
    mockInstrumentedFetch.mockRejectedValue(new Error("Network error"))

    const result = await getReadingsList(3, 0)
    expect(result.entries).toHaveLength(0)
    expect(result.hasMore).toBe(false)
  })

  it("handles mixed success, network error, and non-ok status, omitting failed entries per-day", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(mockDayPayloadResponse("2026-07-23"))
      .mockRejectedValueOnce(new Error("Transport failure"))
      .mockResolvedValueOnce(new Response("Internal Error", { status: 500 }))

    const result = await getReadingsList(3, 0)
    expect(result.entries).toHaveLength(1)
    expect(result.entries[0].date).toBe("2026-07-23")
  })
})
