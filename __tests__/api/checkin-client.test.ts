// ############################################################################
// AI_HEADER: TEST_API_CHECKIN — check-in API client helpers contract.
// ROLE: Proves date helpers and response handling of lib/api/checkin.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-CHECKIN
// purpose: Exercise formatDateInTimeZone, resolveCheckinTargetDate and
//   getCheckin null/response branches of the check-in API client.
// owns:
//   - __tests__/api/checkin-client.test.ts
// inputs: dates, timezones, mock instrumentedFetch responses.
// outputs: assertions on date strings and parsed responses.
// dependencies: lib/api/checkin, instrumentedFetch mock.
// side_effects: none.
// emitted_logs: none.
// invariants: no real network calls.
// failure_policy: assertion failure on contract drift.
// END_MODULE_CONTRACT: M-TEST-API-CHECKIN

// START_MODULE_MAP: M-TEST-API-CHECKIN
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - DATE_HELPERS: timezone formatting and target resolution.
//   - FETCH: getCheckin response/null branches.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-CHECKIN

import { beforeEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import {
  formatDateInTimeZone,
  getCheckin,
  resolveCheckinTargetDate,
} from "@/lib/api/checkin"

beforeEach(() => {
  mockInstrumentedFetch.mockReset()
})

// START_BLOCK: DATE_HELPERS
describe("check-in date helpers", () => {
  it("formats without timezone in local parts", () => {
    const value = new Date(2026, 0, 5, 23, 30)
    expect(formatDateInTimeZone(value, null)).toBe("2026-01-05")
    expect(formatDateInTimeZone(value)).toBe("2026-01-05")
  })

  it("formats in an explicit timezone", () => {
    const value = new Date(Date.UTC(2026, 0, 5, 22, 30))
    expect(formatDateInTimeZone(value, "Europe/Moscow")).toBe("2026-01-06")
  })

  it("resolves explicit ISO target over everything", () => {
    expect(resolveCheckinTargetDate(new Date(), "Europe/Moscow", "2026-07-04")).toBe("2026-07-04")
  })

  it("resolves yesterday in the given timezone", () => {
    const now = new Date(Date.UTC(2026, 0, 5, 22, 30))
    expect(resolveCheckinTargetDate(now, "Europe/Moscow", "yesterday")).toBe("2026-01-05")
  })

  it("falls back to local today for missing or invalid targets", () => {
    const now = new Date(Date.UTC(2026, 0, 5, 22, 30))
    expect(resolveCheckinTargetDate(now, "Europe/Moscow", "garbage")).toBe("2026-01-06")
    expect(resolveCheckinTargetDate(now, "Europe/Moscow", null)).toBe("2026-01-06")
  })
})
// END_BLOCK: DATE_HELPERS

// START_BLOCK: FETCH
describe("getCheckin", () => {
  it("returns the parsed response when a check-in exists", async () => {
    const body = { id: 1, targetDate: "2026-07-05", mood: 4, tags: [] }
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(body), { status: 200 }),
    )

    const result = await getCheckin("2026-07-05")

    expect(result).toEqual(body)
    expect(mockInstrumentedFetch.mock.calls[0][0].url).toBe("/api/checkin/2026-07-05")
  })

  it("returns null when the backend answers with an empty marker", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ checkin: null }), { status: 200 }),
    )

    expect(await getCheckin("2026-07-06")).toBeNull()
  })
})
// END_BLOCK: FETCH

