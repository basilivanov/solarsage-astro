// ############################################################################
// AI_HEADER: MODULE_API_CALENDAR_TEST
// ROLE: Unit and instrumentation wiring tests for lib/api/calendar.ts (Slice 14)
// DEPENDENCIES: vitest, lib/api/calendar, lib/log/instrumented-fetch, e2e/mock-visual/fixtures/day-v2-2026-07-08
// GRACE_ANCHORS: [CALENDAR_API_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-CALENDAR
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, responseContract validators, dayStatus vocabulary normalization, authoritative parse rejections, and reference-equal aliases for calendar facade.
// owns:
//   - __tests__/api/calendar.test.ts
// inputs: mock instrumentedFetch responses, dayPayloadV2 fixture, and month calendar payload
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-CALENDAR (getDayStatus, getMonthCalendar, getMonthStatuses)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-CALENDAR

// START_MODULE_MAP: M-TESTS-CALENDAR
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - DAY_STATUS_TESTS: test getDayStatus operation, route, contract, and vocabulary normalization
//   - MONTH_STATUSES_TESTS: test getMonthStatuses derivation and dayStatus mapping
//   - MONTH_CALENDAR_TESTS: test getMonthCalendar operation, route, contract, and read model validation
//   - ALIAS_TESTS: test reference equality of Async aliases
// owned_tests:
//   - __tests__/api/calendar.test.ts
// END_MODULE_MAP: M-TESTS-CALENDAR

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import {
  getDayStatus,
  getMonthCalendar,
  getMonthStatuses,
  getDayStatusAsync,
  getMonthStatusesAsync,
  getMonthCalendarAsync,
} from "@/lib/api/calendar"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

const calendarPayload = {
  meta: {
    schemaVersion: "calendar/v1",
    contractVersion: 2,
    generatedAt: "2026-05-01T00:00:00Z",
  },
  month: "2026-05",
  title: "May 2026",
  allowedRange: { from: "2024-01-01", to: "2028-12-31" },
  days: [
    {
      date: "2026-05-01",
      dayNumber: 1,
      isCurrentMonth: true,
      isToday: false,
      disabled: false,
      dayStatus: "supportive",
      access: {
        state: "full",
        reason: "active_subscription",
        referralDaysLeft: null,
        subscriptionActive: true,
        accessUntil: "2026-05-01",
      },
      lunar: {
        phase: "waxing_crescent",
        phaseIndex: 1,
        phaseLabel: "раст. серп",
        illumination: 28,
        moonSign: "Taurus",
        moonSignLabel: "Телец",
        lunarDay: 5,
        voidOfCourse: false,
      },
    },
  ],
}

describe("getDayStatus — Slice 14", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches day status via instrumentedFetch with GET /api/day/{date} and TodayPayload contract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(200, { ...dayPayloadV2, dayStatus: "supportive" })
    )

    const date = new Date("2026-07-24T12:00:00Z")
    const status = await getDayStatus(date)

    expect(status).toBe("supportive")
    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "calendar.day_status",
        routeTemplate: "GET /api/day/{date}",
        url: "/api/day/2026-07-24",
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

  it("normalizes dayStatus vocabulary (supportive, tense, steady -> even)", async () => {
    // supportive
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { ...dayPayloadV2, dayStatus: "supportive" }))
    expect(await getDayStatus(new Date("2026-07-24T00:00:00Z"))).toBe("supportive")

    // tense
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { ...dayPayloadV2, dayStatus: "tense" }))
    expect(await getDayStatus(new Date("2026-07-24T00:00:00Z"))).toBe("tense")

    // steady -> even
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { ...dayPayloadV2, dayStatus: "steady" }))
    expect(await getDayStatus(new Date("2026-07-24T00:00:00Z"))).toBe("even")
  })

  it("rejects invalid 200 payload via authoritative TodayPayloadWireSchema parse", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { invalidPayload: true }))
    await expect(getDayStatus(new Date("2026-07-24T00:00:00Z"))).rejects.toThrow()
  })

  it("throws API error status on non-ok or network failure", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(500, { error: "Internal" }))
    await expect(getDayStatus(new Date("2026-07-24T00:00:00Z"))).rejects.toThrow("API error 500")

    mockInstrumentedFetch.mockRejectedValueOnce(new Error("Network disconnect"))
    await expect(getDayStatus(new Date("2026-07-24T00:00:00Z"))).rejects.toThrow("Network disconnect")
  })
})

describe("getMonthStatuses — Slice 14", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("returns DayStatusMap on success normalizing steady to even and ignoring null status", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(200, {
        ...calendarPayload,
        month: "2025-06",
        days: [
          { ...calendarPayload.days[0], date: "2025-06-01", dayStatus: "supportive" },
          { ...calendarPayload.days[0], date: "2025-06-02", dayStatus: "tense" },
          { ...calendarPayload.days[0], date: "2025-06-03", dayStatus: "steady" },
          { ...calendarPayload.days[0], date: "2025-06-04", dayStatus: null },
        ],
      })
    )

    const map = await getMonthStatuses(2025, 5) // zero-based month 5 -> 2025-06
    expect(map).toEqual({
      "2025-06-01": "supportive",
      "2025-06-02": "tense",
      "2025-06-03": "even",
    })
  })

  it("throws on error response", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(404, { detail: "Not found" }))
    await expect(getMonthStatuses(2025, 5)).rejects.toThrow("API error 404")
  })
})

describe("getMonthCalendar — Slice 14", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches month calendar with GET /api/calendar?month=YYYY-MM and CalendarPayloadReadModel contract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, calendarPayload))

    const result = await getMonthCalendar(2026, 4) // zero-based month 4 -> 2026-05

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "calendar.month",
        routeTemplate: "GET /api/calendar",
        url: "/api/calendar?month=2026-05",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "CalendarPayloadReadModel",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(calendarPayload)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )

    expect(result.days[0].access?.state).toBe("full")
    expect(result.days[0].lunar?.phase).toBe("waxing_crescent")
  })

  it("rejects malformed backend calendar payloads via validateCalendarPayloadReadModel", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(200, {
        ...calendarPayload,
        days: [{ ...calendarPayload.days[0], dayStatus: "even" }], // "even" is invalid for backend wire schema
      })
    )

    await expect(getMonthCalendar(2026, 4)).rejects.toThrow()
  })

  it("preserves reference equality for all Async aliases", () => {
    expect(getDayStatusAsync).toBe(getDayStatus)
    expect(getMonthStatusesAsync).toBe(getMonthStatuses)
    expect(getMonthCalendarAsync).toBe(getMonthCalendar)
  })
})
