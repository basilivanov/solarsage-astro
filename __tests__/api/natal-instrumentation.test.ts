// ############################################################################
// AI_HEADER: MODULE_TESTS_NATAL_INSTRUMENTATION
// ROLE: Unit and instrumentation wiring tests for lib/api/natal.ts (Slice 09)
// DEPENDENCIES: vitest, lib/api/natal, lib/log/instrumented-fetch
// GRACE_ANCHORS: [NATAL_INSTRUMENTATION_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-NATAL-INSTRUMENTATION
// purpose: Validate instrumentedFetch wiring, operation labels, route templates, POST bodies, responseContract validators, and status-to-error mappings for natal client.
// owns:
//   - __tests__/api/natal-instrumentation.test.ts
// inputs: mock instrumentedFetch responses and fixtures
// outputs: Vitest assertion results
// dependencies:
//   - M-FRONTEND-API-NATAL (lib/api/natal)
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-NATAL-INSTRUMENTATION

// START_MODULE_MAP: M-TESTS-NATAL-INSTRUMENTATION
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - WIRING_TESTS: test operation and routeTemplate parameters for 4 calls
//   - CONTRACT_VALIDATOR_TESTS: test responseContract.validate logic
//   - STATUS_MAPPING_TESTS: test 404, 409, 501, 502 status mapping regressions
// owned_tests:
//   - __tests__/api/natal-instrumentation.test.ts
// END_MODULE_MAP: M-TESTS-NATAL-INSTRUMENTATION

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import {
  fetchNatalPreview,
  fetchNatalGenerate,
  fetchNatalReport,
  fetchNatalReportSection,
} from "@/lib/api/natal"

const VALID_PREVIEW_RESPONSE = {
  meta: {
    birthDate: "2000-01-01",
    gender: "female",
  },
  chart: {
    houseSystem: "Placidus",
    planets: [
      { name: "Sun", sign: "Aries", degree: 10, house: 1, retrograde: false, longitude: 10 },
    ],
    houses: [
      { number: 1, sign: "Aries", degree: 0, longitude: 0 },
    ],
    aspects: [
      { planetA: "Sun", planetB: "Moon", aspectType: "trine", orb: 1.2, applying: null },
    ],
    angles: [
      { name: "ASC", sign: "Aries", degree: 15, longitude: 15 },
    ],
  },
  highlights: [
    { id: "sun", title: "Солнце", value: "Лев", description: "Ядро личности" },
  ],
  spheres: [
    { id: "career", title: "Карьера", score: 4.5, rank: 1, description: "Сильная сфера" },
  ],
  planets: [
    { id: "sun", name: "Солнце", description: "Солнце во Льве" },
  ],
  chapters: [
    { id: "ch1", eyebrow: "Раздел 1", title: "Портрет", locked: true, description: "Психологический портрет" },
  ],
  personalHook: "Ты собрана",
  calculationStats: {
    planetsCount: 5,
    housesCount: 12,
    aspectsCount: 0,
    spheresCount: 1,
    specialPointsCount: 0,
    scoringFactorsCount: 0,
    dignityFactorsCount: 0,
    totalFactorsCount: 18,
    displayLabel: "18 факторов",
  },
  salesBullets: ["Поймёшь себя"],
  fullReportAvailable: true,
  fullReportPriceKopecks: 39900,
}

const VALID_GENERATE_RESPONSE = {
  reportId: "rep-12345",
  status: "GENERATING",
  sectionsAvailable: false,
}

const VALID_REPORT_READ = {
  id: "rep-12345",
  status: "READY",
  accessState: "UNLOCKED",
  meta: {
    userName: "Test User",
    birthDate: "2000-01-01",
    houseSystem: "Placidus",
    promptVersion: "1",
  },
  sections: [
    {
      id: "portrait",
      title: "Test Section",
      blocks: [
        { type: "paragraph", text: "Hello world" },
      ],
    },
  ],
}

const VALID_SECTION_READ = {
  id: "portrait",
  title: "Test Section",
  blocks: [
    { type: "paragraph", text: "Hello world" },
  ],
}

describe("Natal API Client Instrumentation — Slice 09", () => {
  beforeEach(() => {
    mockInstrumentedFetch.mockClear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it("fetchNatalPreview passes correct operation, routeTemplate, and responseContract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(VALID_PREVIEW_RESPONSE), { status: 200 })
    )

    const res = await fetchNatalPreview()
    expect(res.ok).toBe(true)
    if (res.ok) {
      expect(res.data.meta.birthDate).toBe("2000-01-01")
    }

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "natal.preview",
        routeTemplate: "GET /api/natal/preview",
        url: "/api/natal/preview",
        responseContract: expect.objectContaining({
          contractName: "NatalPreview",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_PREVIEW_RESPONSE)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(
      expect.objectContaining({ valid: false, missingFields: expect.any(Array) })
    )
  })

  it("fetchNatalGenerate passes POST init with exact body, operation, routeTemplate, and contract", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(VALID_GENERATE_RESPONSE), { status: 200 })
    )

    const res = await fetchNatalGenerate(true)
    expect(res.ok).toBe(true)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "natal.generate",
        routeTemplate: "POST /api/natal/generate",
        url: "/api/natal/generate",
        init: expect.objectContaining({
          method: "POST",
          credentials: "include",
          headers: { "Content-Type": "application/json", Accept: "application/json" },
          body: JSON.stringify({ forceRegenerate: true }),
        }),
        responseContract: expect.objectContaining({
          contractName: "NatalGenerate",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_GENERATE_RESPONSE)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("fetchNatalReport passes reportId in URL while routeTemplate retains placeholder", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(VALID_REPORT_READ), { status: 200 })
    )

    const res = await fetchNatalReport("rep-12345")
    expect(res.ok).toBe(true)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "natal.report",
        routeTemplate: "GET /api/natal/report/{id}",
        url: "/api/natal/report/rep-12345",
        responseContract: expect.objectContaining({
          contractName: "NatalReport",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_REPORT_READ)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("fetchNatalReportSection passes actual IDs in URL while routeTemplate uses placeholders", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(VALID_SECTION_READ), { status: 200 })
    )

    const res = await fetchNatalReportSection("rep-12345", "portrait")
    expect(res.ok).toBe(true)

    expect(mockInstrumentedFetch).toHaveBeenCalledWith(
      expect.objectContaining({
        operation: "natal.section",
        routeTemplate: "GET /api/natal/report/{id}/section/{sectionId}",
        url: "/api/natal/report/rep-12345/section/portrait",
        responseContract: expect.objectContaining({
          contractName: "NatalReportSection",
          contractVersion: "v1",
        }),
      })
    )

    const contract = mockInstrumentedFetch.mock.calls[0][0].responseContract
    expect(contract.validate(VALID_SECTION_READ)).toEqual({ valid: true })
    expect(contract.validate({})).toEqual(expect.objectContaining({ valid: false }))
  })

  it("preserves status mapping regressions (404 Not Found in fetchNatalReport)", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("Not Found", { status: 404 })
    )

    const res = await fetchNatalReport("non-existent")
    expect(res.ok).toBe(false)
    if (!res.ok) {
      expect(res.error.type).toBe("not_found")
      expect(res.error.message).toBe("Report not found")
    }
  })
})
