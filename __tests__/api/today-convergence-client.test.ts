// ############################################################################
// AI_HEADER: TEST_API_TODAY_CONVERGENCE_CLIENT — today convergence API client.
// ROLE: Proves retry 200/202 branches and best-effort impression swallow.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-TODAY-CONVERGENCE-CLIENT
// purpose: Exercise retryTodayConvergence and recordDayImpression branches.
// owns:
//   - __tests__/api/today-convergence-client.test.ts
// inputs: mock instrumentedFetch responses.
// outputs: assertions on normalized retry results and swallowed telemetry.
// dependencies: lib/api/today-convergence, instrumentedFetch mock.
// side_effects: none.
// emitted_logs: none (mocked transport).
// invariants: impression never throws.
// failure_policy: assertion failure on contract drift.
// END_MODULE_CONTRACT: M-TEST-API-TODAY-CONVERGENCE-CLIENT

// START_MODULE_MAP: M-TEST-API-TODAY-CONVERGENCE-CLIENT
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - RETRY: 200 payload and 202 Retry-After branches.
//   - IMPRESSION: ok/error/swallow branches.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-TODAY-CONVERGENCE-CLIENT

import { beforeEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

vi.mock("@/lib/log", () => ({
  logEvent: vi.fn(),
}))

import { recordDayImpression, retryTodayConvergence } from "@/lib/api/today-convergence"
import heroTense from "../fixtures/today_convergence_v2/02_hero_tense.json"

beforeEach(() => {
  mockInstrumentedFetch.mockReset()
})

// START_BLOCK: RETRY
describe("retryTodayConvergence", () => {
  it("returns payload for an immediate 200", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(heroTense), { status: 200 }),
    )

    const result = await retryTodayConvergence("today")

    expect(result.payload).toBeDefined()
    expect(result.retryAfterSeconds).toBeUndefined()
    expect(mockInstrumentedFetch.mock.calls[0][0].url).toBe("/api/day/today/retry")
  })

  it("returns retryAfterSeconds for a 202 acceptance", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("{}", { status: 202, headers: { "Retry-After": "17" } }),
    )

    const result = await retryTodayConvergence("2026-08-01")

    expect(result.payload).toBeUndefined()
    expect(result.retryAfterSeconds).toBe(17)
  })

  it("returns undefined retryAfterSeconds when the header is absent", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("{}", { status: 202 }),
    )

    const result = await retryTodayConvergence("2026-08-01")

    expect(result.retryAfterSeconds).toBeUndefined()
  })
})
// END_BLOCK: RETRY

// START_BLOCK: IMPRESSION
describe("recordDayImpression", () => {
  it("posts the day surface impression without throwing", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response(null, { status: 204 }))

    await expect(recordDayImpression("snap-1")).resolves.toBeUndefined()

    const call = mockInstrumentedFetch.mock.calls[0][0]
    expect(call.url).toBe("/api/day/snapshots/snap-1/impression")
    expect(call.init.body).toBe(JSON.stringify({ surface: "day" }))
  })

  it("swallows http rejections", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(new Response("{}", { status: 404 }))

    await expect(recordDayImpression("snap-2")).resolves.toBeUndefined()
  })

  it("swallows transport failures", async () => {
    mockInstrumentedFetch.mockRejectedValueOnce(new TypeError("offline"))

    await expect(recordDayImpression("snap-3")).resolves.toBeUndefined()
  })
})
// END_BLOCK: IMPRESSION
