// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_START_V2_PREVIEW
// ROLE: Test-only one-command launcher: mock API on 18092 + Next dev on 3003.
// DEPENDENCIES: node http, child_process, node fs, node path, node url, node net
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-START-V2-PREVIEW
// purpose: Start local mock API + Next preview for V2 personal day UX review.
// owns:
//   - e2e/mock-visual/start-v2-preview.mjs
// inputs: JSON fixtures under e2e/mock-visual/fixtures/json/
// outputs: HTTP mock on 127.0.0.1:18092, Next on 0.0.0.0:3003
// dependencies: node http, child_process, local fixture JSON only
// side_effects: binds ports, spawns next, writes process lifecycle
// emitted_logs: stdout preview URL and lifecycle
// invariants:
//   - Never falls through to production API
//   - Fail fast if ports occupied
//   - SIGINT/SIGTERM terminate children
//   - next-env.d.ts is restored atomic-safely if modified by Next.js
//   - tsconfig.json is restored atomic-safely if modified by Next.js
// failure_policy: exit non-zero on bind/start failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-START-V2-PREVIEW

import http from "node:http"
import { spawn } from "node:child_process"
import { readFileSync, existsSync, writeFileSync, renameSync, unlinkSync, statSync, accessSync, constants } from "node:fs"
import { join, dirname, basename } from "node:path"
import { fileURLToPath } from "node:url"
import net from "node:net"
import process from "node:process"

const __dirname = dirname(fileURLToPath(import.meta.url))
const ROOT = join(__dirname, "../..")
const FIX_DIR = join(__dirname, "fixtures/json")

const MOCK_HOST = "127.0.0.1"
const MOCK_PORT = 18092
const NEXT_HOST = "0.0.0.0"
const NEXT_PORT = 3003

function loadJson(name) {
  const p = join(FIX_DIR, name)
  if (!existsSync(p)) {
    throw new Error(`Missing fixture JSON: ${p}`)
  }
  return JSON.parse(readFileSync(p, "utf8"))
}

function portFree(host, port) {
  return new Promise((resolve) => {
    const s = net.createServer()
    s.once("error", () => resolve(false))
    s.once("listening", () => s.close(() => resolve(true)))
    s.listen(port, host)
  })
}

function sendJson(res, status, body) {
  const payload = JSON.stringify(body)
  res.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(payload),
    "Cache-Control": "no-store",
  })
  res.end(payload)
}

function createMockServer() {
  // Acceptance override: serve the exact audit payload instead of the bundled
  // fixture when ACCEPTANCE_PAYLOAD_PATH points at a produced artifact JSON.
  const overridePath = process.env.ACCEPTANCE_PAYLOAD_PATH
  const dayV2 = overridePath
    ? JSON.parse(readFileSync(overridePath, "utf-8"))
    : loadJson("day-v2-2026-07-08.json")
  const week = loadJson("week-neighbours.json")
  const calendar = loadJson("calendar-2026-07.json")
  const profile = loadJson("profile.json")
  const referral = loadJson("referral.json")

  const dayByDate = {
    [overridePath ? dayV2.date : "2026-07-08"]: dayV2,
    ...week,
  }

  return http.createServer((req, res) => {
    const url = new URL(req.url || "/", `http://${MOCK_HOST}:${MOCK_PORT}`)
    const path = url.pathname

    if (req.method === "OPTIONS") {
      res.writeHead(204)
      res.end()
      return
    }

    if (path.startsWith("/api/day/")) {
      const date = path.slice("/api/day/".length)
      const body = dayByDate[date]
      if (body) {
        sendJson(res, 200, body)
        return
      }
      sendJson(res, 501, {
        detail: "missing_mock_visual_fixture",
        path,
      })
      return
    }

    if (path === "/api/calendar") {
      sendJson(res, 200, calendar)
      return
    }

    if (path === "/api/auth/dev" && (req.method === "POST" || req.method === "GET")) {
      sendJson(res, 200, { status: "ok", userId: "mock-preview-user" })
      return
    }

    if (path === "/api/profile") {
      sendJson(res, 200, profile)
      return
    }

    if (path === "/api/referral") {
      sendJson(res, 200, referral)
      return
    }

    if (path === "/api/_log") {
      sendJson(res, 200, { ok: true })
      return
    }

    if (path.startsWith("/api/")) {
      sendJson(res, 501, {
        detail: "missing_mock_visual_fixture",
        path,
      })
      return
    }

    sendJson(res, 404, { detail: "not_found", path })
  })
}

// strict safety regex to reject legacy .next-v2-preview
function isSafeBasename(name) {
  return /^\.next-v2-preview-[A-Za-z0-9_-]+$/.test(name)
}

// Atomic file helper: write to temp file in same directory + rename
function atomicWriteFile(targetPath, bytes, mode) {
  const dir = dirname(targetPath)
  const base = basename(targetPath)
  const tempPath = join(dir, `${base}.tmp.${process.pid}`)
  try {
    writeFileSync(tempPath, bytes, { mode })
    renameSync(tempPath, targetPath)
  } catch (err) {
    try {
      if (existsSync(tempPath)) unlinkSync(tempPath)
    } catch { /* ignore */ }
    throw err;
  }
}

async function main() {
  const mockFree = await portFree(MOCK_HOST, MOCK_PORT)
  if (!mockFree) {
    console.error(`[preview:v2] Port ${MOCK_PORT} already occupied. Aborting.`)
    process.exit(1)
  }
  const nextFree = await portFree(NEXT_HOST, NEXT_PORT)
  if (!nextFree) {
    const nextFreeLocal = await portFree("127.0.0.1", NEXT_PORT)
    if (!nextFreeLocal) {
      console.error(`[preview:v2] Port ${NEXT_PORT} already occupied. Aborting.`)
      process.exit(1)
    }
  }

  // 1. User-specific disposable dist dir
  const currentUid = typeof process.getuid === "function" ? process.getuid() : "default"
  let distDir = `.next-v2-preview-${currentUid}`

  // Support safe NEXT_DIST_DIR override
  if (process.env.NEXT_DIST_DIR) {
    const override = process.env.NEXT_DIST_DIR
    if (isSafeBasename(override)) {
      distDir = override
    } else {
      console.error(`[preview:v2] Error: NEXT_DIST_DIR override '${override}' is unsafe. Rejecting.`)
      process.exit(1)
    }
  }

  const distPath = join(ROOT, distDir)
  // Verify selected directory is readable, writable, and traversable if it exists
  if (existsSync(distPath)) {
    try {
      accessSync(distPath, constants.R_OK | constants.W_OK | constants.X_OK)
    } catch {
      console.error(`[preview:v2] Error: Selected cache directory '${distDir}' is not fully accessible (R/W/X). Aborting.`)
      process.exit(1)
    }
  }

  // Next CLI existence check
  const nextCliPath = join(ROOT, "node_modules/next/dist/bin/next")
  if (!existsSync(nextCliPath)) {
    console.error(`[preview:v2] Error: Next CLI not found at '${nextCliPath}'. Please run pnpm install.`)
    process.exit(1)
  }

  // 2. Original state capture
  const envFile = join(ROOT, "next-env.d.ts")
  let originalEnvBytes = null
  let originalEnvMode = 0o644
  if (existsSync(envFile)) {
    try {
      originalEnvBytes = readFileSync(envFile)
      originalEnvMode = statSync(envFile).mode & 0o777
    } catch {
      console.error(`[preview:v2] Warning: Could not read existing next-env.d.ts.`)
    }
  }

  const tsconfigFile = join(ROOT, "tsconfig.json")
  let originalTsconfigBytes = null
  let originalTsconfigMode = 0o644
  if (existsSync(tsconfigFile)) {
    try {
      originalTsconfigBytes = readFileSync(tsconfigFile)
      originalTsconfigMode = statSync(tsconfigFile).mode & 0o777
    } catch {
      console.error(`[preview:v2] Warning: Could not read existing tsconfig.json.`)
    }
  }

  const mock = createMockServer()
  await new Promise((resolve, reject) => {
    mock.once("error", reject)
    mock.listen(MOCK_PORT, MOCK_HOST, resolve)
  })
  console.log(`[preview:v2] Mock API listening on http://${MOCK_HOST}:${MOCK_PORT}`)

  const env = {
    ...process.env,
    NODE_ENV: "development",
    NEXT_DIST_DIR: distDir,
    DEV_API_REWRITE_BASE_URL: `http://${MOCK_HOST}:${MOCK_PORT}`,
  }

  // Spawn Next CLI directly through current Node executable
  const next = spawn(
    process.execPath,
    [nextCliPath, "dev", "--hostname", NEXT_HOST, "--port", String(NEXT_PORT)],
    {
      cwd: ROOT,
      env,
      stdio: "inherit",
    },
  )

  let shuttingDown = false

  function restoreEnvFile() {
    if (originalEnvBytes === null) return

    if (existsSync(envFile)) {
      const currentBytes = readFileSync(envFile)
      if (Buffer.compare(currentBytes, originalEnvBytes) === 0) {
        return
      }

      // Four exact Buffer candidates for LF/CRLF variants
      const expectedTemplate = (importPath, newline) =>
        `/// <reference types="next" />${newline}` +
        `/// <reference types="next/image-types/global" />${newline}` +
        `import "${importPath}";${newline}${newline}` +
        `// NOTE: This file should not be edited${newline}` +
        `// see https://nextjs.org/docs/app/api-reference/config/typescript for more information.${newline}`

      const candidate1LF = Buffer.from(expectedTemplate(`./${distDir}/types/routes.d.ts`, "\n"), "utf8")
      const candidate1CRLF = Buffer.from(expectedTemplate(`./${distDir}/types/routes.d.ts`, "\r\n"), "utf8")
      const candidate2LF = Buffer.from(expectedTemplate(`./${distDir}/dev/types/routes.d.ts`, "\n"), "utf8")
      const candidate2CRLF = Buffer.from(expectedTemplate(`./${distDir}/dev/types/routes.d.ts`, "\r\n"), "utf8")

      const isMatch =
        Buffer.compare(currentBytes, candidate1LF) === 0 ||
        Buffer.compare(currentBytes, candidate1CRLF) === 0 ||
        Buffer.compare(currentBytes, candidate2LF) === 0 ||
        Buffer.compare(currentBytes, candidate2CRLF) === 0

      if (isMatch) {
        console.log(`[preview:v2] Restoring next-env.d.ts byte-safely...`)
        try {
          atomicWriteFile(envFile, originalEnvBytes, originalEnvMode)
        } catch (err) {
          console.error(`[preview:v2] Error during next-env.d.ts restoration:`, err)
        }
      } else {
        console.warn(`[preview:v2] Warning: next-env.d.ts contains unexpected changes. Leaving it for manual review.`)
      }
    }
  }

  function restoreTsconfigFile() {
    if (originalTsconfigBytes === null) return

    if (existsSync(tsconfigFile)) {
      const currentBytes = readFileSync(tsconfigFile)
      if (Buffer.compare(currentBytes, originalTsconfigBytes) === 0) {
        return
      }

      // Semantic-exact tsconfig.json recognition
      try {
        const originalJson = JSON.parse(originalTsconfigBytes.toString("utf8"))
        const currentJson = JSON.parse(currentBytes.toString("utf8"))

        // Create copies to isolate changes
        const currentCopy = JSON.parse(JSON.stringify(currentJson))

        // Check if "include" key exists and matches modifications
        if (Array.isArray(currentCopy.include) && Array.isArray(originalJson.include)) {
          const expectedEntries = [
            `${distDir}/types/**/*.ts`,
            `${distDir}/dev/types/**/*.ts`
          ]

          // Verify each expected entry appears exactly once in the current include array
          const entryCounts = expectedEntries.map(entry => currentCopy.include.filter(e => e === entry).length)
          const allExactOnce = entryCounts.every(count => count === 1)

          if (allExactOnce) {
            // Filter out exactly the two UID-cache entries from currentCopy.include
            const originalLen = originalJson.include.length
            const currentLen = currentCopy.include.length

            if (currentLen === originalLen + 2) {
              const filteredInclude = currentCopy.include.filter(entry => !expectedEntries.includes(entry))

              // Check if the filtered include matches the original include exactly (same items, same order)
              const matchesOriginal = JSON.stringify(filteredInclude) === JSON.stringify(originalJson.include)
              if (matchesOriginal) {
                // Revert include list for deep equality check
                currentCopy.include = originalJson.include

                if (JSON.stringify(currentCopy) === JSON.stringify(originalJson)) {
                  console.log(`[preview:v2] Restoring tsconfig.json byte-safely...`)
                  atomicWriteFile(tsconfigFile, originalTsconfigBytes, originalTsconfigMode)
                  return
                }
              }
            }
          }
        }

        console.warn(`[preview:v2] Warning: tsconfig.json contains unexpected changes. Leaving it for manual review.`)
      } catch (err) {
        console.error(`[preview:v2] Error during tsconfig.json parsing/restoration:`, err)
      }
    }
  }

  function finalize() {
    restoreEnvFile()
    restoreTsconfigFile()
  }

  // Bounded shutdown state machine
  function shutdown(code = 0) {
    if (shuttingDown) return
    shuttingDown = true
    console.log("[preview:v2] Shutting down...")

    // Close mock server
    try {
      mock.close()
    } catch { /* ignore */ }

    // Bounded wait state machine for direct child exit
    if (next.exitCode === null && next.signalCode === null) {
      console.log("[preview:v2] Sending SIGTERM to Next child...")
      next.kill("SIGTERM")

      let waitTimer = 0
      const interval = setInterval(() => {
        waitTimer += 100
        if (next.exitCode !== null || next.signalCode !== null) {
          clearInterval(interval)
          finalize()
          process.exit(code)
        } else if (waitTimer >= 5000) {
          clearInterval(interval)
          console.log("[preview:v2] Next child did not exit within 5s. Sending SIGKILL...")
          next.kill("SIGKILL")

          let killTimer = 0
          const killInterval = setInterval(() => {
            killTimer += 100
            if (next.exitCode !== null || next.signalCode !== null || killTimer >= 2000) {
              clearInterval(killInterval)
              finalize()
              process.exit(code)
            }
          }, 100)
        }
      }, 100)
    } else {
      finalize()
      process.exit(code)
    }
  }

  process.on("SIGINT", () => shutdown(0))
  process.on("SIGTERM", () => shutdown(0))

  next.on("exit", (code) => {
    if (!shuttingDown) {
      console.error(`[preview:v2] Next exited with code ${code}`)
      shutdown(code ?? 1)
    }
  })

  next.on("error", (err) => {
    console.error(`[preview:v2] Next process error:`, err)
    if (!shuttingDown) {
      shutdown(1)
    }
  })

  console.log(`[preview:v2] http://127.0.0.1:3003/day/2026-07-08`)
  console.log("[preview:v2] TEST-ONLY mock visual preview. Do not use for production.")
}

main().catch((err) => {
  console.error("[preview:v2] Fatal:", err)
  process.exit(1)
})
