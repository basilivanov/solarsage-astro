// ############################################################################
// AI_HEADER: TEST_API_NATAL_PREVIEW — natal preview client branches.
// ROLE: Proves 409/error/zod/network branches of fetchNatalPreview.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-NATAL-PREVIEW
// purpose: Exercise fetchNatalPreview success and failure branch matrix.
// owns:
//   - __tests__/api/natal-preview.test.ts
// inputs: mock instrumentedFetch responses.
// outputs: assertions on ok/error result shapes.
// dependencies: lib/api/natal, instrumentedFetch mock.
// side_effects: none.
// emitted_logs: none.
// invariants: no real network calls.
// failure_policy: assertion failure on contract drift.
// END_MODULE_CONTRACT: M-TEST-API-NATAL-PREVIEW

// START_MODULE_MAP: M-TEST-API-NATAL-PREVIEW
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - BRANCHES: 200/409/500/zod/network matrix.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-NATAL-PREVIEW

import { beforeEach, describe, expect, it, vi } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { fetchNatalPreview } from "@/lib/api/natal"

beforeEach(() => {
  mockInstrumentedFetch.mockReset()
})

const validPreview = {
  meta: {
    name: "Тест",
    birthDate: "1990-01-15",
    birthTime: "12:00",
    birthCity: "Москва, Россия",
    gender: "male",
  },
  chart: null,
  highlights: [],
  spheres: [],
  planets: [],
  chapters: [],
  personalHook: "Короткий крючок",
  calculationStats: {
    planetsCount: 10,
    housesCount: 12,
    aspectsCount: 15,
    spheresCount: 12,
    specialPointsCount: 2,
    scoringFactorsCount: 30,
    dignityFactorsCount: 5,
    totalFactorsCount: 37,
    displayLabel: "37 факторов",
  },
  salesBullets: [],
  fullReportAvailable: true,
  fullReportPriceKopecks: 99000,
}

// START_BLOCK: BRANCHES
describe("fetchNatalPreview", () => {
  it("returns ok=true with parsed preview for 200", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validPreview), { status: 200 }),
    )

    const result = await fetchNatalPreview()

    expect(result.ok).toBe(true)
    expect(mockInstrumentedFetch.mock.calls[0][0].url).toBe("/api/natal/preview")
  })

  it("maps 409 to profile_incomplete with missing fields", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(
        JSON.stringify({ detail: { message: "no coords", missingFields: ["birthLat"] } }),
        { status: 409 },
      ),
    )

    const result = await fetchNatalPreview()

    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("profile_incomplete")
      expect(result.error).toMatchObject({ missingFields: ["birthLat"] })
    }
  })

  it("maps other http failures to a generic error", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ message: "boom" }), { status: 500 }),
    )

    const result = await fetchNatalPreview()

    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.error.type).toBe("error")
  })

  it("maps zod-invalid 200 payload to format error", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ nope: true }), { status: 200 }),
    )

    const result = await fetchNatalPreview()

    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.error.message).toContain("Invalid response format")
  })

  it("maps transport failures to network error", async () => {
    mockInstrumentedFetch.mockRejectedValueOnce(new TypeError("offline"))

    const result = await fetchNatalPreview()

    expect(result.ok).toBe(false)
    if (!result.ok) expect(result.error.message).toBe("Network error")
  })
})
// END_BLOCK: BRANCHES
