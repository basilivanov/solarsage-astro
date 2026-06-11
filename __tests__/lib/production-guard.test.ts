
// ############################################################################
// AI_HEADER: MODULE_LIB_PRODUCTION_GUARD_TEST
// ROLE: Unit tests for production-guard.test.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Unit tests for production-guard.test.ts — __tests__/lib/production-guard.test.ts
// owns:
//   - __tests__/lib/production-guard.test.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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

  it("allows demo mode true in Vercel preview when override is set even if NODE_ENV is production", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("VERCEL_ENV", "preview")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "true")
    expect(() => assertProductionSafety()).not.toThrow()
  })

  it("allows demo mode true in staging when override is set even if NODE_ENV is production", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("APP_ENV", "staging")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "true")
    expect(() => assertProductionSafety()).not.toThrow()
  })

  it("throws in Vercel preview when demo mode is true and override is not set", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("VERCEL_ENV", "preview")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "false")
    expect(() => assertProductionSafety()).toThrow("Unsafe preview config")
  })

  it("throws in Vercel production environment when demo mode is true even if ALLOW_DEMO_MODE_IN_PREVIEW is true", () => {
    vi.stubEnv("NODE_ENV", "production")
    vi.stubEnv("VERCEL_ENV", "production")
    vi.stubEnv("NEXT_PUBLIC_DEMO_MODE", "true")
    vi.stubEnv("ALLOW_DEMO_MODE_IN_PREVIEW", "true")
    expect(() => assertProductionSafety()).toThrow("Unsafe production config")
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
