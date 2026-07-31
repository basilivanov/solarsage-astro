// ############################################################################
// AI_HEADER: MODULE_API_READINGS_TEST — day-history client and catalog tests.
// ROLE: Unit tests for the published snapshot history facade and static readings catalog.
// DEPENDENCIES: vitest, lib/api/readings, lib/log/instrumented-fetch, generated day-history zod schema
// GRACE_ANCHORS: [READINGS_DAY_HISTORY_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-READINGS
// purpose: Validate day-history request wiring, zod validation, snapshot mapping and the stable product catalog.
// owns:
//   - __tests__/api/readings.test.ts
// inputs: mock instrumentedFetch responses and canonical day-history payloads.
// outputs: Vitest assertion results.
// dependencies:
//   - M-FRONTEND-API-READINGS (getReadingsList, listReadings)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness).
// failure_policy: raise assertions.
// END_MODULE_CONTRACT: M-TESTS-READINGS

// START_MODULE_MAP: M-TESTS-READINGS
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - CATALOG_TESTS: test static listReadings catalog output
//   - HISTORY_DAY_HISTORY_TESTS: test one-request day-history wiring, validation and fail-soft handling
// owned_tests:
//   - __tests__/api/readings.test.ts
// END_MODULE_MAP: M-TESTS-READINGS

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { getReadingsList, listReadings } from "@/lib/api/readings"

const dayHistoryPayload = {
  access: {
    state: "full" as const,
    subscriptionActive: true,
    referralDaysLeft: null,
    accessUntil: null,
    reason: "active_subscription" as const,
  },
  items: [
    {
      date: "2026-07-30",
      snapshotId: "snapshot-2026-07-30",
      state: "convergence_today" as const,
      dayTone: "supportive" as const,
      sphereKeys: ["work", "relationships"],
      impulseCount: 3,
    },
    {
      date: "2026-07-29",
      snapshotId: "snapshot-2026-07-29",
      state: "quiet_day" as const,
      dayTone: "steady" as const,
      sphereKeys: [],
      impulseCount: 0,
    },
  ],
}

function mockDayHistoryResponse(body: unknown = dayHistoryPayload, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("listReadings catalog", () => {
  it("returns catalog with available and coming arrays", () => {
    const catalog = listReadings()
    expect(catalog.available).toBeDefined()
    expect(catalog.coming).toBeDefined()
    expect(Array.isArray(catalog.available)).toBe(true)
    expect(Array.isArray(catalog.coming)).toBe(true)
  })

  it("available includes natal and horary readings", () => {
    const catalog = listReadings()
    expect(catalog.available.map((reading) => reading.key)).toContain("natal")
    expect(catalog.available.map((reading) => reading.key)).toContain("horary")
  })
})

describe("getReadingsList — published day-history", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches one day-history payload with the exact limit query", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse())

    const result = await getReadingsList(2)

    expect(result).toEqual({
      entries: dayHistoryPayload.items,
      hasMore: true,
      access: dayHistoryPayload.access,
    })
    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "readings.day_history",
        routeTemplate: "GET /api/readings/day-history",
        url: "/api/readings/day-history?limit=2",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "DayHistoryPayload",
          contractVersion: "v1",
        }),
      }),
    )
  })

  it("preserves only snapshot summary fields, not legacy Today reading fields", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse())

    const result = await getReadingsList(2)
    expect(result.entries[0]).toMatchObject({
      date: "2026-07-30",
      snapshotId: "snapshot-2026-07-30",
      state: "convergence_today",
      dayTone: "supportive",
      sphereKeys: ["work", "relationships"],
      impulseCount: 3,
    })
    expect(result.entries[0]).not.toHaveProperty("headline")
    expect(result.entries[0]).not.toHaveProperty("dayStatus")
    expect(result.entries[0]).not.toHaveProperty("preview")
    expect(result.entries[0]).not.toHaveProperty("paragraphs")
  })

  it("uses the zod response contract for valid and malformed payloads", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse())

    await getReadingsList(1)

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(dayHistoryPayload)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) }),
    )
  })

  it("does not fan out into N /api/day calls", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse())

    await getReadingsList(10)

    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
    expect(mockInstrumentedFetch.mock.calls[0][0].url).toBe(
      "/api/readings/day-history?limit=10",
    )
  })

  it("returns an empty history for invalid, non-ok or rejected responses", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse({ items: [] }))
    await expect(getReadingsList(2)).resolves.toMatchObject({ entries: [], hasMore: false })

    mockInstrumentedFetch.mockReset()
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse({}, 200))
    await expect(getReadingsList(2)).resolves.toMatchObject({ entries: [], hasMore: false })

    mockInstrumentedFetch.mockReset()
    mockInstrumentedFetch.mockResolvedValueOnce(mockDayHistoryResponse("Internal Error", 500))
    await expect(getReadingsList(2)).resolves.toMatchObject({ entries: [], hasMore: false })

    mockInstrumentedFetch.mockReset()
    mockInstrumentedFetch.mockRejectedValueOnce(new Error("Network error"))
    await expect(getReadingsList(2)).resolves.toMatchObject({ entries: [], hasMore: false })
  })
})
