// ############################################################################
// AI_HEADER: MODULE_LIB_VERCEL_ANALYTICS_TEST — truth-table tests for shouldRenderVercelAnalytics.
// ROLE: Unit tests for the deployment-boundary analytics gate.
// DEPENDENCIES: @/lib/analytics/vercel
// GRACE_ANCHORS: []
// SLICE: SLICE-TESTS
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Test every row of the shouldRenderVercelAnalytics truth table
//   and verify that app/layout.tsx delegates to the helper.
// owns:
//   - __tests__/lib/vercel-analytics.test.ts
// inputs: Fixtures for various NODE_ENV/VERCEL combinations.
// outputs: Assertion results.
// dependencies:
//   - @/lib/analytics/vercel (shouldRenderVercelAnalytics)
// side_effects: n/a (tests)
// emitted_logs: n/a (tests)
// invariants:
//   - Only NODE_ENV=production AND VERCEL=1 returns true.
// failure_policy: log and raise
// END_MODULE_CONTRACT

import { describe, it, expect } from "vitest"
import { shouldRenderVercelAnalytics } from "@/lib/analytics/vercel"

describe("shouldRenderVercelAnalytics", () => {
  // Truth table from TZ section 5

  it("returns true when NODE_ENV=production and VERCEL=1", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production", VERCEL: "1" })).toBe(true)
  })

  it("returns false when NODE_ENV=production and VERCEL absent", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production" })).toBe(false)
  })

  it("returns false when NODE_ENV=production and VERCEL=0", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production", VERCEL: "0" })).toBe(false)
  })

  it("returns false when NODE_ENV=development and VERCEL=1", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "development", VERCEL: "1" })).toBe(false)
  })

  it("returns false when NODE_ENV=test and VERCEL=1", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "test", VERCEL: "1" })).toBe(false)
  })

  // Malformed / partial input

  it("returns false when NODE_ENV is undefined and VERCEL is undefined", () => {
    expect(shouldRenderVercelAnalytics({})).toBe(false)
  })

  it("returns false when NODE_ENV is undefined and VERCEL=1", () => {
    expect(shouldRenderVercelAnalytics({ VERCEL: "1" })).toBe(false)
  })

  it("returns false when NODE_ENV=production and VERCEL is arbitrary non-empty string", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production", VERCEL: "true" })).toBe(false)
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production", VERCEL: "yes" })).toBe(false)
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "production", VERCEL: "VERCEL" })).toBe(false)
  })

  it("returns false when NODE_ENV is empty string and VERCEL=1", () => {
    expect(shouldRenderVercelAnalytics({ NODE_ENV: "", VERCEL: "1" })).toBe(false)
  })
})

describe("layout.tsx delegates analytics to shouldRenderVercelAnalytics", () => {
  it("imports and calls the helper from app/layout.tsx", async () => {
    // Read layout source and verify it imports the helper and uses it
    const fs = await import("node:fs")
    const source = fs.readFileSync("app/layout.tsx", "utf8")

    // Verify the import exists
    expect(source).toContain('shouldRenderVercelAnalyticsFromEnv')
    expect(source).toContain('"@/lib/analytics/vercel"')

    // Verify the old NODE_ENV-only condition is gone
    expect(source).not.toContain('process.env.NODE_ENV === "production" && <Analytics />')

    // Verify the new condition uses the helper
    expect(source).toContain('{shouldRenderVercelAnalyticsFromEnv() && <Analytics />}')
  })
})
