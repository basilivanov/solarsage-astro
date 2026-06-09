import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { assertProductionSafety } from "../../lib/env/production-guard"
import { fetchDay } from "../../lib/grace/api/client"

describe("assertProductionSafety", () => {
  const origEnv = { ...process.env }

  beforeEach(() => {
    // Clear relevant env vars
    vi.stubEnv("NODE_ENV", "")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "")
    vi.stubEnv("APP_ENV", "")
    vi.stubEnv("VERCEL_ENV", "")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
  })

  it("allows demo mode true in development", () => {
    vi.stubEnv("NODE_ENV", "development")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    expect(() => assertProductionSafety()).not.toThrow()
  })

  it("throws in production when demo mode is true", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    expect(() => assertProductionSafety()).toThrow("Unsafe production config")
  })

  it("does not throw in production when demo mode is false", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "false")
    expect(() => assertProductionSafety()).not.toThrow()
  })

  it("throws in preview/staging when demo mode is true without override", () => {
    vi.stubEnv("APP_ENV", "preview")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    expect(() => assertProductionSafety()).toThrow("Unsafe preview config")
  })

  it("allows in preview/staging when demo mode is true and override is set", () => {
    vi.stubEnv("APP_ENV", "preview")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "true")
    expect(() => assertProductionSafety()).not.toThrow()
  })
})

describe("API error does not return demo payload in production", () => {
  const origEnv = { ...process.env }

  beforeEach(() => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "false")
  })

  afterEach(() => {
    vi.unstubAllEnvs()
    vi.restoreAllMocks()
  })

  it("throws an error and does not return DEMO_TODAY_RESPONSE when API returns 500", async () => {
    global.fetch = vi.fn().mockResolvedValue({
      ok: false,
      status: 500,
      statusText: "Internal Server Error",
      json: async () => ({ detail: "Internal Server Error" }),
    })

    await expect(fetchDay("2026-06-09")).rejects.toThrow()
  })
})
