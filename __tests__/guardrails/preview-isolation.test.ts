import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import { join } from "node:path"

/**
 * Guard: production Next config must ignore DEV_API_REWRITE_BASE_URL.
 * Guard: product runtime must not import preview fixtures.
 */
describe("preview isolation guards", () => {
  it("next.config ignores DEV_API_REWRITE_BASE_URL in production", () => {
    const src = readFileSync(join(process.cwd(), "next.config.mjs"), "utf8")
    expect(src).toContain("DEV_API_REWRITE_BASE_URL")
    expect(src).toMatch(/NODE_ENV\s*===\s*["']production["']/)
    // must not import fixture/mock modules
    expect(src).not.toMatch(/mock-visual|day-v2-2026|fixtures\//)
  })

  it("product runtime paths do not import e2e mock-visual fixtures", () => {
    const roots = ["app", "components", "hooks", "lib"]
    // Match real imports only — not comments that mention the harness path.
    const importRe =
      /(?:from\s+|import\s*(?:\(\s*)?|require\s*\(\s*)["']([^"']*(?:e2e\/mock-visual|mock-visual\/fixtures|start-v2-preview)[^"']*)["']/g
    const { readdirSync, statSync } = require("node:fs") as typeof import("node:fs")
    const { join: j } = require("node:path") as typeof import("node:path")

    function walk(dir: string): string[] {
      const out: string[] = []
      for (const entry of readdirSync(dir)) {
        if (entry === "node_modules" || entry.startsWith(".")) continue
        const p = j(dir, entry)
        const st = statSync(p)
        if (st.isDirectory()) out.push(...walk(p))
        else if (/\.(ts|tsx|js|mjs)$/.test(entry) && !entry.includes(".test.")) out.push(p)
      }
      return out
    }

    const violations: string[] = []
    for (const root of roots) {
      for (const file of walk(root)) {
        const text = readFileSync(file, "utf8")
        for (const m of text.matchAll(importRe)) {
          violations.push(`${file}: imports ${m[1]}`)
        }
      }
    }
    expect(violations).toEqual([])
  })
})
