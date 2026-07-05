import { describe, expect, it } from "vitest"

describe("resolveNextDistDir", () => {
  it("uses .next-prod in production", async () => {
    // @ts-ignore - mjs helper intentionally has no TS build step
    const { resolveNextDistDir } = await import("../../lib/env/next-dist-dir.mjs")
    expect(resolveNextDistDir({ NODE_ENV: "production" })).toBe(".next-prod")
  })

  it("uses .next outside production", async () => {
    // @ts-ignore - mjs helper intentionally has no TS build step
    const { resolveNextDistDir } = await import("../../lib/env/next-dist-dir.mjs")
    expect(resolveNextDistDir({ NODE_ENV: "development" })).toBe(".next")
  })

  it("allows explicit NEXT_DIST_DIR override", async () => {
    // @ts-ignore - mjs helper intentionally has no TS build step
    const { resolveNextDistDir } = await import("../../lib/env/next-dist-dir.mjs")
    expect(resolveNextDistDir({ NODE_ENV: "production", NEXT_DIST_DIR: ".custom-next" })).toBe(".custom-next")
  })
})
