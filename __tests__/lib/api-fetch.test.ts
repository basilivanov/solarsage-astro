// ############################################################################
// AI_HEADER: MODULE_TESTS_API_FETCH
// ROLE: Unit tests for lib/api-fetch.ts (Slice 17)
// DEPENDENCIES: vitest, lib/api-fetch, lib/log/instrumented-fetch
// GRACE_ANCHORS: [API_FETCH_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-API-FETCH
// purpose: Validate method prefix normalization, timeout separation from RequestInit, options immutability, and transparent instrumentedFetch delegation in apiFetch.
// owns:
//   - __tests__/lib/api-fetch.test.ts
// inputs: mock instrumentedFetch responses and ApiFetchOptions
// outputs: Vitest assertion results
// dependencies:
//   - M-API-FETCH (apiFetch)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-API-FETCH

// START_MODULE_MAP: M-TESTS-API-FETCH
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - METHOD_NORMALIZATION_TESTS: test method prefix uppercase normalization and duplicate prevention
//   - TIMEOUT_SEPARATION_TESTS: test default 30000ms timeout and timeout exclusion from init
//   - IMMUTABILITY_TESTS: test options object immutability
//   - DELEGATION_TESTS: test transparent Response return and rejection propagation
// owned_tests:
//   - __tests__/lib/api-fetch.test.ts
// END_MODULE_MAP: M-TESTS-API-FETCH

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { apiFetch, type ApiFetchOptions } from "@/lib/api-fetch"

describe("apiFetch — Slice 17 Compatibility Facade", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("uses default GET method prefix and 30000ms timeout when options are omitted", async () => {
    const mockRes = new Response(JSON.stringify({ ok: true }), { status: 200 })
    mockInstrumentedFetch.mockResolvedValueOnce(mockRes)

    const res = await apiFetch("/api/profile", "/api/profile")
    expect(res).toBe(mockRes)

    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(1)
    expect(mockInstrumentedFetch).toHaveBeenCalledWith({
      operation: "/api/profile",
      routeTemplate: "GET /api/profile",
      url: "/api/profile",
      init: {},
      timeoutMs: 30000,
    })
  })

  it("handles custom PATCH without duplicating method prefix in routeTemplate", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response("OK", { status: 200 }))

    await apiFetch("PATCH /api/user", "/api/user", { method: "PATCH" })

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        routeTemplate: "PATCH /api/user",
      })
    )
  })

  it("normalizes lowercase method prefix like 'delete /api/item' to 'DELETE /api/item'", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response("OK", { status: 200 }))

    await apiFetch("delete /api/item/123", "/api/item/123")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        routeTemplate: "DELETE /api/item/123",
      })
    )
  })

  it("separates custom timeout from init and passes custom timeoutMs", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response("OK", { status: 200 }))

    const abortController = new AbortController()
    const options: ApiFetchOptions = {
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Test" }),
      signal: abortController.signal,
      timeout: 5000,
    }

    await apiFetch("POST /api/test", "/api/test", options)

    const callArg = mockInstrumentedFetch.mock.calls[0][0]
    expect(callArg.timeoutMs).toBe(5000)

    // Key timeout NEVER exists inside init!
    expect((callArg.init as any).timeout).toBeUndefined()
    expect(callArg.init).toEqual({
      method: "POST",
      credentials: "include",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ name: "Test" }),
      signal: abortController.signal,
    })
  })

  it("does not mutate the input options object", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response("OK", { status: 200 }))

    const inputOptions: ApiFetchOptions = {
      method: "PUT",
      headers: { Authorization: "Bearer token" },
      timeout: 8000,
    }

    const copy = { ...inputOptions }
    await apiFetch("PUT /api/resource", "/api/resource", inputOptions)

    expect(inputOptions).toEqual(copy)
  })

  it("passes through network rejection and Response objects transparently", async () => {
    // Case 1: Rejection
    mockInstrumentedFetch.mockRejectedValueOnce(new TypeError("Failed to fetch"))
    await expect(apiFetch("GET /api/test", "/api/test")).rejects.toThrow("Failed to fetch")

    // Case 2: 500 Response
    const errorRes = new Response("Error", { status: 500 })
    mockInstrumentedFetch.mockResolvedValueOnce(errorRes)
    const res = await apiFetch("GET /api/test", "/api/test")
    expect(res.status).toBe(500)
    expect(res).toBe(errorRes)
  })
})
