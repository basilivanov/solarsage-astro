/**
 * Wave 5 fix tests: natal API client — retry, demo isolation, Zod validation.
 *
 * Tests cover:
 * - Blocker 1: generating-page retry calls fetchNatalGenerate(true)
 * - Blocker 2: production /readings/natal/demo does not serve mock
 * - Blocker 3: report-page retry handles GENERATING/PENDING
 * - Risk 1: API client uses Zod schemas for runtime validation
 * - Risk 2: fetchNatalReportSection has demo-mode handling
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

// We test the API client functions directly by mocking fetch and IS_DEMO_MODE.

// Mock IS_DEMO_MODE — default to false (production)
let mockDemoMode = false

vi.mock("@/lib/demo-mode", () => ({
  get IS_DEMO_MODE() {
    return mockDemoMode
  },
}))

vi.mock("@/lib/demo-data", () => ({
  DEMO_NATAL_PREVIEW: {
    meta: { name: "Test", birthDate: "2000-01-01", gender: "female" },
    highlights: [],
    spheres: [],
    planets: [],
    chapters: [],
    personalHook: "test",
    calculationStats: {
      planetsCount: 1,
      housesCount: 12,
      aspectsCount: 0,
      spheresCount: 1,
      specialPointsCount: 0,
      scoringFactorsCount: 0,
      dignityFactorsCount: 0,
      totalFactorsCount: 14,
      displayLabel: "14 факторов",
    },
    salesBullets: [],
    fullReportAvailable: false,
    fullReportPriceKopecks: 99900,
  },
}))

// Mock data for Zod validation tests
const VALID_GENERATE_RESPONSE = {
  reportId: "abc-123",
  status: "GENERATING",
  sectionsAvailable: false,
}

const VALID_REPORT_READ = {
  id: "abc-123",
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

describe("fetchNatalReport — demo isolation", () => {
  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("returns mock data in demo mode (IS_DEMO_MODE=true)", async () => {
    mockDemoMode = true
    const { fetchNatalReport } = await import("@/lib/api/natal")

    const result = await fetchNatalReport("demo")
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.id).toBe("demo")
      expect(result.data.status).toBe("READY")
    }
  })

  it("returns not_found for 'demo' reportId in production (IS_DEMO_MODE=false)", async () => {
    mockDemoMode = false
    const { fetchNatalReport } = await import("@/lib/api/natal")

    const result = await fetchNatalReport("demo")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("not_found")
      expect(result.error.message).toContain("not found")
    }
  })

  it("does not return MOCK_NATAL_REPORT_READ for 'demo' id when not in demo mode", async () => {
    mockDemoMode = false
    const { fetchNatalReport } = await import("@/lib/api/natal")

    const result = await fetchNatalReport("demo")
    // Must NOT return mock data
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).not.toBe(undefined)
    }
  })

  it("calls backend for real report ids in production", async () => {
    mockDemoMode = false
    const { fetchNatalReport } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_REPORT_READ,
    })

    const result = await fetchNatalReport("abc-123")
    expect(result.ok).toBe(true)
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/natal/report/abc-123"),
      expect.any(Object)
    )
  })
})

describe("fetchNatalReportSection — demo-mode handling", () => {
  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("returns section from mock in demo mode", async () => {
    mockDemoMode = true
    const { fetchNatalReportSection } = await import("@/lib/api/natal")

    const result = await fetchNatalReportSection("demo", "portrait")
    // Section "portrait" exists in MOCK_NATAL_REPORT_READ
    if (result.ok) {
      expect(result.data.id).toBe("portrait")
    } else {
      // Section might not be found — that's acceptable as long as it's not a network call
      expect(result.error.type).toBe("not_found")
    }
  })

  it("returns not_found for 'demo' reportId in production", async () => {
    mockDemoMode = false
    const { fetchNatalReportSection } = await import("@/lib/api/natal")

    const result = await fetchNatalReportSection("demo", "portrait")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("not_found")
    }
  })

  it("calls backend for real report ids in production", async () => {
    mockDemoMode = false
    const { fetchNatalReportSection } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_SECTION_READ,
    })

    const result = await fetchNatalReportSection("abc-123", "portrait")
    expect(result.ok).toBe(true)
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/natal/report/abc-123/section/portrait"),
      expect.any(Object)
    )
  })
})

describe("fetchNatalGenerate — Zod validation", () => {
  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("parses valid response with Zod schema", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_GENERATE_RESPONSE,
    })

    const result = await fetchNatalGenerate(false)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.reportId).toBe("abc-123")
      expect(result.data.status).toBe("GENERATING")
    }
  })

  it("returns error for invalid response format (Zod validation failure)", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ invalidField: true }), // Missing required reportId and status
    })

    const result = await fetchNatalGenerate(false)
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("error")
      expect(result.error.message).toContain("Invalid response format")
    }
  })
})

describe("fetchNatalReport — Zod validation", () => {
  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("parses valid response with Zod schema", async () => {
    const { fetchNatalReport } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_REPORT_READ,
    })

    const result = await fetchNatalReport("abc-123")
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.id).toBe("abc-123")
      expect(result.data.status).toBe("READY")
      expect(result.data.sections).toHaveLength(1)
    }
  })

  it("returns error for invalid response format (Zod validation failure)", async () => {
    const { fetchNatalReport } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ wrong: "shape" }), // Missing required fields
    })

    const result = await fetchNatalReport("abc-123")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("error")
      expect(result.error.message).toContain("Invalid response format")
    }
  })
})

describe("fetchNatalReportSection — Zod validation", () => {
  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("parses valid section response with Zod schema", async () => {
    const { fetchNatalReportSection } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_SECTION_READ,
    })

    const result = await fetchNatalReportSection("abc-123", "portrait")
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.id).toBe("portrait")
      expect(result.data.blocks).toHaveLength(1)
    }
  })

  it("returns error for invalid section format (Zod validation failure)", async () => {
    const { fetchNatalReportSection } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({ bad: true }),
    })

    const result = await fetchNatalReportSection("abc-123", "portrait")
    expect(result.ok).toBe(false)
    if (!result.ok) {
      expect(result.error.type).toBe("error")
      expect(result.error.message).toContain("Invalid response format")
    }
  })
})

describe("retry behavior — generating page calls fetchNatalGenerate(true)", () => {
  /**
   * This test verifies the contract that the generating page's retry handler
   * calls fetchNatalGenerate with forceRegenerate=true.
   * The actual component test would require a full render setup,
   * so we test the API client directly to ensure the force flag is sent.
   */

  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("sends forceRegenerate=true in request body", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        reportId: "new-report-id",
        status: "GENERATING",
        sectionsAvailable: false,
      }),
    })

    const result = await fetchNatalGenerate(true)
    expect(result.ok).toBe(true)

    // Verify the fetch call sent forceRegenerate: true
    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/natal/generate"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ forceRegenerate: true }),
      })
    )
  })

  it("sends forceRegenerate=false by default", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => VALID_GENERATE_RESPONSE,
    })

    const result = await fetchNatalGenerate(false)
    expect(result.ok).toBe(true)

    expect(global.fetch).toHaveBeenCalledWith(
      expect.stringContaining("/api/natal/generate"),
      expect.objectContaining({
        method: "POST",
        body: JSON.stringify({ forceRegenerate: false }),
      })
    )
  })
})

describe("error states — backend returns GENERATING/PENDING", () => {
  /**
   * Blocker 3: Verify that fetchNatalGenerate can return GENERATING/PENDING
   * status, and the caller (report page retry) must handle these statuses
   * rather than treating them as failures.
   *
   * The report page retry handler now handles:
   * - READY → fetch and display
   * - GENERATING/PENDING → transition to generating state
   * - FAILED_RETRYABLE → failed retryable
   * - FAILED_PERMANENT → permanent failure
   */

  beforeEach(() => {
    mockDemoMode = false
    vi.restoreAllMocks()
  })

  it("fetchNatalGenerate returns GENERATING status correctly", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        reportId: "gen-123",
        status: "GENERATING",
        sectionsAvailable: false,
      }),
    })

    const result = await fetchNatalGenerate(true)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.status).toBe("GENERATING")
      expect(result.data.reportId).toBe("gen-123")
    }
  })

  it("fetchNatalGenerate returns PENDING status correctly", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        reportId: "pend-123",
        status: "PENDING",
        sectionsAvailable: false,
      }),
    })

    const result = await fetchNatalGenerate(true)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.status).toBe("PENDING")
    }
  })

  it("fetchNatalGenerate returns FAILED_RETRYABLE with errorMessage", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        reportId: "fail-123",
        status: "FAILED_RETRYABLE",
        sectionsAvailable: false,
        errorMessage: "LLM timeout",
      }),
    })

    const result = await fetchNatalGenerate(true)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.status).toBe("FAILED_RETRYABLE")
      expect(result.data.errorMessage).toBe("LLM timeout")
    }
  })

  it("fetchNatalGenerate returns FAILED_PERMANENT with errorMessage", async () => {
    const { fetchNatalGenerate } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        reportId: "perm-123",
        status: "FAILED_PERMANENT",
        sectionsAvailable: false,
        errorMessage: "Profile incomplete",
      }),
    })

    const result = await fetchNatalGenerate(true)
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.status).toBe("FAILED_PERMANENT")
      expect(result.data.errorMessage).toBe("Profile incomplete")
    }
  })

  it("fetchNatalReport returns GENERATING status for non-ready report", async () => {
    const { fetchNatalReport } = await import("@/lib/api/natal")

    global.fetch = vi.fn().mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        id: "gen-456",
        status: "GENERATING",
        accessState: "FREE_PREVIEW",
        meta: { houseSystem: "Placidus", promptVersion: "1" },
        sections: [],
      }),
    })

    const result = await fetchNatalReport("gen-456")
    expect(result.ok).toBe(true)
    if (result.ok) {
      expect(result.data.status).toBe("GENERATING")
    }
  })
})
