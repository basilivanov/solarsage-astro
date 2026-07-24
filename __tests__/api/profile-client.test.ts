// ############################################################################
// AI_HEADER: MODULE_TESTS_PROFILE_CLIENT
// ROLE: Unit and instrumentation wiring tests for lib/api/profile.ts (Slice 16)
// DEPENDENCIES: vitest, lib/api/profile, lib/log/instrumented-fetch
// GRACE_ANCHORS: [PROFILE_CLIENT_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PROFILE-CLIENT
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, PUT bodies, ProfileRead responseContract validator, HTTP error priority, and invalid shape rejection for profile client.
// owns:
//   - __tests__/api/profile-client.test.ts
// inputs: mock instrumentedFetch responses and ProfileRead wire fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-PROFILE (getProfile, updateProfile)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PROFILE-CLIENT

// START_MODULE_MAP: M-TESTS-PROFILE-CLIENT
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation, routeTemplate, init, body and responseContract for GET and PUT
//   - CONTRACT_VALIDATOR_TESTS: test responseContract.validate logic and authoritative parse rejection
//   - ERROR_DECODE_TESTS: test detail string, detail.message, array messages, and fallback error priority
// owned_tests:
//   - __tests__/api/profile-client.test.ts
// END_MODULE_MAP: M-TESTS-PROFILE-CLIENT

import { beforeEach, afterEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { getProfile, updateProfile } from "@/lib/api/profile"

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    statusText: status === 200 ? "OK" : "ERR",
    headers: { "Content-Type": "application/json" },
  })
}

const VALID_PROFILE_READ = {
  userId: "11111111-1111-1111-1111-111111111111",
  birth: {
    birthday: "1990-01-01",
    birthTime: "12:00",
    birthCity: "Moscow",
    birthLat: 55.75,
    birthLon: 37.62,
    birthTz: "Europe/Moscow",
  },
  firstName: "Test User",
  gender: "female",
  isOnboarded: true,
}

describe("getProfile & updateProfile — Slice 16 Instrumentation & Contracts", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("getProfile passes correct operation, routeTemplate, headers, credentials, and ProfileRead responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, VALID_PROFILE_READ))

    const profile = await getProfile()
    expect(profile.userId).toBe("11111111-1111-1111-1111-111111111111")
    expect(profile.firstName).toBe("Test User")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "profile.get",
        routeTemplate: "GET /api/profile",
        url: "/api/profile",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "ProfileRead",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PROFILE_READ)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("updateProfile passes PUT init with exact body, operation, routeTemplate, and ProfileRead responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(200, VALID_PROFILE_READ))

    const updatePayload = {
      firstName: "Updated Name",
      gender: "female" as const,
    }

    const profile = await updateProfile(updatePayload)
    expect(profile.userId).toBe("11111111-1111-1111-1111-111111111111")

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "profile.update",
        routeTemplate: "PUT /api/profile",
        url: "/api/profile",
        init: expect.objectContaining({
          method: "PUT",
          credentials: "include",
          headers: { Accept: "application/json", "Content-Type": "application/json" },
          body: JSON.stringify(updatePayload),
        }),
        responseContract: expect.objectContaining({
          contractName: "ProfileRead",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PROFILE_READ)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("rejects HTTP 200 response with invalid profile shape (non-UUID userId) via authoritative Zod parse", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(200, { ...VALID_PROFILE_READ, userId: "not-a-valid-uuid" })
    )

    await expect(getProfile()).rejects.toThrow()
  })

  it("decodes HTTP errors according to priority: detail string -> detail.message -> validation array -> fallback", async () => {
    // 1. Detail string
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(400, { detail: "String detail error" }))
    await expect(getProfile()).rejects.toThrow("String detail error")

    // 2. Object detail.message
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(400, { detail: { message: "Object detail message" } }))
    await expect(getProfile()).rejects.toThrow("Object detail message")

    // 3. Validation array messages
    mockInstrumentedFetch.mockResolvedValueOnce(
      jsonResponse(422, {
        detail: [
          { msg: "First field invalid" },
          { msg: "Second field missing" },
        ],
      })
    )
    await expect(getProfile()).rejects.toThrow("First field invalid. Second field missing")

    // 4. Fallback string
    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(500, {}))
    await expect(getProfile()).rejects.toThrow("Failed to get profile")

    mockInstrumentedFetch.mockResolvedValueOnce(jsonResponse(500, {}))
    await expect(updateProfile({})).rejects.toThrow("Failed to update profile")
  })
})
