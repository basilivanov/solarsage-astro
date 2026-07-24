// ############################################################################
// AI_HEADER: MODULE_API_ACCESS_TEST
// ROLE: Unit and instrumentation wiring tests for lib/api/access.ts (Slice 12)
// DEPENDENCIES: vitest, lib/api/access, lib/log/instrumented-fetch
// GRACE_ANCHORS: [ACCESS_API_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-API-ACCESS
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, AccessSummary responseContract validator, HTTP error detail mapping, and invalid shape rejection for getAccess.
// owns:
//   - __tests__/api/access.test.ts
// inputs: mock instrumentedFetch responses and AccessSummary wire fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-ACCESS (getAccess)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-API-ACCESS

// START_MODULE_MAP: M-TESTS-API-ACCESS
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation, routeTemplate, init and responseContract
//   - MAPPING_TESTS: test toAccessInfo mapping for trial, subscription, expired
//   - ERROR_TESTS: test HTTP error message priority and invalid 200 payload rejection
// owned_tests:
//   - __tests__/api/access.test.ts
// END_MODULE_MAP: M-TESTS-API-ACCESS

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { getAccess } from "@/lib/api/access"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

const VALID_ACCESS_SUMMARY = {
  user: "trial",
  referralDaysLeft: 8,
  subscriptionActive: false,
  accessStart: "2026-07-01",
  accessUntil: "2026-07-08",
}

describe("getAccess — Slice 12 Instrumentation & Contracts", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetches the authenticated backend access summary via instrumentedFetch with AccessSummary contract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, VALID_ACCESS_SUMMARY))

    const info = await getAccess()

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "access.get",
        routeTemplate: "GET /api/access",
        url: "/api/access",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "AccessSummary",
          contractVersion: "v1",
        }),
      })
    )

    // Test validator
    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_ACCESS_SUMMARY)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )

    expect(info).toEqual({
      state: "trial",
      hasAccess: true,
      accessStart: new Date("2026-07-01T00:00:00"),
      accessEnd: new Date("2026-07-08T00:00:00"),
      daysLeft: 8,
    })
  })

  it("maps subscription and expired summaries without synthetic durations", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        jsonResponse(200, {
          user: "subscription",
          referralDaysLeft: 0,
          subscriptionActive: true,
          accessStart: "2026-07-01",
          accessUntil: "2026-07-30",
        })
      )
      .mockResolvedValueOnce(
        jsonResponse(200, {
          user: "expired",
          referralDaysLeft: 0,
          subscriptionActive: false,
          accessStart: "2026-05-01",
          accessUntil: "2026-05-30",
        })
      )

    const subscription = await getAccess()
    const expired = await getAccess()

    expect(subscription.state).toBe("subscription")
    expect(subscription.daysLeft).toBe(0)
    expect(subscription.accessEnd).toEqual(new Date("2026-07-30T00:00:00"))
    expect(expired).toMatchObject({
      state: "expired",
      hasAccess: false,
      daysLeft: 0,
    })
  })

  it("rejects HTTP 200 response with invalid shape via authoritative Zod parse", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, { user: "invalid_user_state" }))

    await expect(getAccess()).rejects.toThrow()
  })

  it("throws the backend detail on HTTP errors", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(401, { detail: { message: "Session expired" } })
    )

    await expect(getAccess()).rejects.toThrow("Session expired")
  })
})
