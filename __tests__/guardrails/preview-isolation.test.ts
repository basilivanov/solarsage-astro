// ############################################################################
// AI_HEADER: MODULE_PREVIEW_ISOLATION_TEST — guardrail test suite for preview isolation.
// ROLE: Verifies that product runtime and configuration files do not import dev-fixtures or E2E visual fixtures.
// DEPENDENCIES: node_modules/node:fs, node_modules/node:path, vitest
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-PREVIEW-ISOLATION
// purpose: Guard production builds from leaking local dev/E2E mock visual fixtures.
// owns:
//   - __tests__/guardrails/preview-isolation.test.ts
// inputs: files in app, components, hooks, lib directories.
// outputs: vitest assertions.
// dependencies: fs, path.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - No static imports of mock-visual or dev-fixtures are allowed in product code.
//   - The only exception is dynamic await import in app/api/dev-fixtures/three-horizon-timing/route.ts, situated after security guards.
// failure_policy: fail test.
// END_MODULE_CONTRACT: M-TEST-PREVIEW-ISOLATION

// START_MODULE_MAP: M-TEST-PREVIEW-ISOLATION
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - ISOLATION_TESTS: validates production configuration and static import rules.
// owned_tests:
//   - __tests__/guardrails/preview-isolation.test.ts
// END_MODULE_MAP: M-TEST-PREVIEW-ISOLATION

// START_BLOCK: ISOLATION_TESTS
import { describe, it, expect } from "vitest"
import { readFileSync } from "node:fs"
import { join } from "node:path"

describe("preview isolation guards", () => {
  it("next.config ignores DEV_API_REWRITE_BASE_URL in production", () => {
    const src = readFileSync(join(process.cwd(), "next.config.mjs"), "utf8")
    expect(src).toContain("DEV_API_REWRITE_BASE_URL")
    expect(src).toMatch(/NODE_ENV\s*===\s*["']production["']/)
    // must not import fixture/mock modules
    expect(src).not.toMatch(/mock-visual|day-v2-2026|fixtures\//)
  })

  it("next.config sets a rewrite proxyTimeout that covers synchronous generation", () => {
    const src = readFileSync(join(process.cwd(), "next.config.mjs"), "utf8")
    // Synchronous MVP endpoints (natal report generation) exceed the 30 s
    // default; production nginx allows 300 s, so the rewrite must match it.
    expect(src).toContain("proxyTimeout")
    expect(src).toMatch(/proxyTimeout:\s*300_?000/)
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
    let allowedImportCount = 0
    for (const root of roots) {
      for (const file of walk(root)) {
        const text = readFileSync(file, "utf8")
        for (const m of text.matchAll(importRe)) {
          // Rule 2 & 3: The only exception is dynamic await import in app/api/dev-fixtures/three-horizon-timing/route.ts
          if (file === "app/api/dev-fixtures/three-horizon-timing/route.ts") {
            const allowedSpecifier = "../../../../e2e/mock-visual/fixtures/day-v2-2026-07-08"
            const matchIndex = m.index ?? -1
            const hasExactSpecifier = m[1] === allowedSpecifier
            const hasExactForm =
              matchIndex >= 6
              && m[0].startsWith(`import("${allowedSpecifier}"`)
              && text.slice(matchIndex - 6, matchIndex) === "await "

            // Rule 4: Verify it occurs after development, local dev host, and proxy checks
            const idxDev = text.indexOf('process.env.NODE_ENV !== "development"')
            const idxHost = text.indexOf('!isLocalDevHost')
            const idxProxy = text.indexOf('hasUnsafeProxyOriginHeaders')
            const idx404 = text.indexOf('return NextResponse.json({ error: "Not found" }, { status: 404 })')

            const hasDevelopmentGuard = idxDev >= 0 && idxDev < matchIndex
            const hasHostGuard = idxHost >= 0 && idxHost < matchIndex
            const hasProxyGuard = idxProxy >= 0 && idxProxy < matchIndex
            const has404Guard = idx404 >= 0 && idx404 < matchIndex

            if (hasExactSpecifier && hasExactForm && hasDevelopmentGuard && hasHostGuard && hasProxyGuard && has404Guard) {
              allowedImportCount++
              if (allowedImportCount === 1) {
                continue
              }
            }
          }
          violations.push(`${file}: imports ${m[1]}`)
        }
      }
    }
    expect(violations).toEqual([])
    expect(allowedImportCount).toBe(1)
  })

  describe("production API rewrite base branches", () => {
    const evalRewrites = (env: NodeJS.ProcessEnv): string => {
      const { execFileSync } = require("node:child_process") as typeof import("node:child_process")
      return execFileSync(
        process.execPath,
        [
          "-e",
          `(async () => {
            const cfg = (await import("./next.config.mjs")).default;
            const rw = await cfg.rewrites();
            process.stdout.write(JSON.stringify(rw));
          })();`,
        ],
        { cwd: process.cwd(), env: { ...process.env, ...env }, encoding: "utf8" },
      )
    }

    it("honors PROD_API_REWRITE_BASE_URL in production (canonical Compose http://api:8000)", () => {
      const out = evalRewrites({ NODE_ENV: "production", PROD_API_REWRITE_BASE_URL: "http://api:8000" })
      expect(out).toContain('"destination":"http://api:8000/api/:path*"')
    })

    it("falls back to the canonical local API in production without the override", () => {
      const env: NodeJS.ProcessEnv = { NODE_ENV: "production" }
      delete env.PROD_API_REWRITE_BASE_URL
      const out = evalRewrites(env)
      expect(out).toContain('"destination":"http://127.0.0.1:8000/api/:path*"')
    })

    it("keeps ignoring DEV_API_REWRITE_BASE_URL in production", () => {
      const out = evalRewrites({
        NODE_ENV: "production",
        DEV_API_REWRITE_BASE_URL: "http://dev-host:9999",
      })
      expect(out).toContain('"destination":"http://127.0.0.1:8000/api/:path*"')
    })

    it("still honors DEV_API_REWRITE_BASE_URL outside production", () => {
      const out = evalRewrites({
        NODE_ENV: "development",
        DEV_API_REWRITE_BASE_URL: "http://dev-host:9999",
      })
      expect(out).toContain('"destination":"http://dev-host:9999/api/:path*"')
    })

    it("canonical frontend image bakes PROD_API_REWRITE_BASE_URL before pnpm build", () => {
      const src = readFileSync(join(process.cwd(), "apps/web/Dockerfile"), "utf8")
      // Builder stage must define the non-secret build arg and export it into
      // the build environment before the pnpm build step, otherwise
      // routes-manifest falls back to the loopback destination inside the image.
      const argIdx = src.indexOf("ARG PROD_API_REWRITE_BASE_URL=http://api:8000")
      const envIdx = src.indexOf("PROD_API_REWRITE_BASE_URL=${PROD_API_REWRITE_BASE_URL}")
      const buildIdx = src.indexOf("RUN pnpm build")
      expect(argIdx).toBeGreaterThan(-1)
      expect(envIdx).toBeGreaterThan(-1)
      expect(buildIdx).toBeGreaterThan(-1)
      expect(argIdx).toBeLessThan(buildIdx)
      expect(envIdx).toBeLessThan(buildIdx)
    })
  })
})
// END_BLOCK: ISOLATION_TESTS
