// ############################################################################
// AI_HEADER: MODULE_API_PROFILE_META_TEST
// ROLE: Unit tests for lib/api/profile-meta.ts (Slice 06)
// DEPENDENCIES: vitest, lib/api/profile-meta, lib/log/instrumented-fetch
// GRACE_ANCHORS: [PROFILE_META_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-PROFILE-META
// purpose: Validate fail-soft aggregation, instrumentedFetch call wiring, HoraryQuota contract validation, and fallback behavior for getProfileMeta.
// owns:
//   - __tests__/api/profile-meta.test.ts
// inputs: mock instrumentedFetch responses and fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-PROFILE-META (getProfileMeta)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-PROFILE-META

// START_MODULE_MAP: M-TESTS-PROFILE-META
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - AGGREGATION_TESTS: test business defaults, mapping and fail-soft fallbacks
//   - INSTRUMENTATION_TESTS: test instrumentedFetch operation/routeTemplate and contract validation
// owned_tests:
//   - __tests__/api/profile-meta.test.ts
// END_MODULE_MAP: M-TESTS-PROFILE-META

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { getProfileMeta, getProfileMetaAsync } from "@/lib/api/profile-meta"

describe("getProfileMeta — Slice 06", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("passes exact operation, routeTemplate, credentials, and Accept header for both calls", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            weeklyFreeAvailable: true,
            bonusCredits: 1,
            paidCredits: 2,
            canPurchase: true,
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ totalInvited: 2, inviteUrl: "https://t.me/ref" }),
          { status: 200 }
        )
      )

    const result = await getProfileMeta()

    expect(mockInstrumentedFetch).toHaveBeenCalledTimes(2)

    // Call 1: Horary quota
    expect(mockInstrumentedFetch).toHaveBeenNthCalledWith(
      1,
      expect.objectContaining({
        operation: "profile_meta.horary_quota",
        routeTemplate: "GET /api/horary/quota",
        url: "/api/horary/quota",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
        responseContract: expect.objectContaining({
          contractName: "HoraryQuota",
          contractVersion: "v1",
        }),
      })
    )

    // Call 2: Referral
    expect(mockInstrumentedFetch).toHaveBeenNthCalledWith(
      2,
      expect.objectContaining({
        operation: "profile_meta.referral",
        routeTemplate: "GET /api/referral",
        url: "/api/referral",
        init: {
          credentials: "include",
          headers: { Accept: "application/json" },
        },
      })
    )

    expect(result.horary.weeklyFreeAvailable).toBe(true)
    expect(result.referral.count).toBe(2)
  })

  it("quota responseContract validates correct quota shape and flags invalid shape", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))
      .mockResolvedValueOnce(new Response("{}", { status: 200 }))

    await getProfileMeta()

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract).toBeDefined()

    const validQuota = {
      weeklyFreeAvailable: true,
      bonusCredits: 1,
      paidCredits: 0,
      canPurchase: false,
    }
    expect(contract.validate(validQuota)).toEqual({ valid: true })

    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("returns default values when both calls fail", async () => {
    mockInstrumentedFetch.mockRejectedValue(new Error("Network error"))

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.horary.bonusCredits).toBe(0)
    expect(result.horary.paidCredits).toBe(0)
    expect(result.horary.canPurchase).toBe(false)
    expect(result.referral.count).toBe(0)
    expect(result.referral.inviteUrl).toBe("")
  })

  it("returns defaults when one promise is rejected (Promise.all catch fallback)", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            weeklyFreeAvailable: true,
            bonusCredits: 5,
          }),
          { status: 200 }
        )
      )
      .mockRejectedValueOnce(new Error("Referral service down"))

    const result = await getProfileMeta()

    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.horary.bonusCredits).toBe(0)
    expect(result.referral.count).toBe(0)
  })

  it("returns quota data on success when referral returns non-ok status", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            weeklyFreeAvailable: true,
            weeklyFreeExpiresAt: "2026-12-31T00:00:00Z",
            bonusCredits: 2,
            paidCredits: 3,
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(new Response("Internal error", { status: 500 }))

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(true)
    expect(result.horary.weeklyFreeExpiresAt).toBe("2026-12-31T00:00:00Z")
    expect(result.horary.bonusCredits).toBe(2)
    expect(result.horary.paidCredits).toBe(3)
    expect(result.horary.canPurchase).toBe(false)
    expect(result.referral.count).toBe(0)
  })

  it("handles quota with missing optional fields", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            weeklyFreeAvailable: false,
            bonusCredits: 1,
            paidCredits: 0,
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(new Response("Not found", { status: 404 }))

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.horary.bonusCredits).toBe(1)
    expect(result.horary.paidCredits).toBe(0)
    expect(result.horary.weeklyFreeExpiresAt).toBeNull()
    expect(result.horary.canPurchase).toBe(false)
  })

  it("returns referral data on success when quota returns non-ok status", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(new Response("Unauthorized", { status: 401 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ totalInvited: 3, inviteUrl: "https://t.me/bot?start=ref123" }),
          { status: 200 }
        )
      )

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(false)
    expect(result.referral.count).toBe(3)
    expect(result.referral.inviteUrl).toBe("https://t.me/bot?start=ref123")
    expect(result.referral.bonusDays).toBe(42)
  })

  it("maps daysPerInvite from backend to rewardDays and computes bonusDays", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(new Response("Error", { status: 500 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ totalInvited: 3, daysPerInvite: 21, inviteUrl: "url" }),
          { status: 200 }
        )
      )

    const result = await getProfileMeta()
    expect(result.referral.rewardDays).toBe(21)
    expect(result.referral.bonusDays).toBe(63) // 3 * 21
    expect(result.referral.count).toBe(3)
  })

  it("defaults rewardDays to 14 when daysPerInvite is missing", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(new Response("Error", { status: 500 }))
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ totalInvited: 1, inviteUrl: "url" }),
          { status: 200 }
        )
      )

    const result = await getProfileMeta()
    expect(result.referral.rewardDays).toBe(14)
    expect(result.referral.bonusDays).toBe(14) // 1 * 14
  })

  it("returns both horary and referral when both endpoints succeed", async () => {
    mockInstrumentedFetch
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({
            weeklyFreeAvailable: true,
            bonusCredits: 0,
            paidCredits: 2,
          }),
          { status: 200 }
        )
      )
      .mockResolvedValueOnce(
        new Response(
          JSON.stringify({ totalInvited: 1, inviteUrl: "url" }),
          { status: 200 }
        )
      )

    const result = await getProfileMeta()
    expect(result.horary.weeklyFreeAvailable).toBe(true)
    expect(result.horary.paidCredits).toBe(2)
    expect(result.referral.count).toBe(1)
  })

  it("ensures getProfileMetaAsync is reference-equal to getProfileMeta", () => {
    expect(getProfileMetaAsync).toBe(getProfileMeta)
  })
})
