// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_START_V2_PREVIEW
// ROLE: Test-only one-command launcher: mock API on 18092 + Next dev on 3003.
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
// failure_policy: exit non-zero on bind/start failure
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-START-V2-PREVIEW

import http from "node:http"
import { spawn } from "node:child_process"
import { readFileSync, existsSync } from "node:fs"
import { join, dirname } from "node:path"
import { fileURLToPath } from "node:url"
import net from "node:net"

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
  const dayV2 = loadJson("day-v2-2026-07-08.json")
  const week = loadJson("week-neighbours.json")
  const calendar = loadJson("calendar-2026-07.json")
  const profile = loadJson("profile.json")
  const referral = loadJson("referral.json")

  const dayByDate = {
    "2026-07-08": dayV2,
    ...week,
  }

  return http.createServer((req, res) => {
    const url = new URL(req.url || "/", `http://${MOCK_HOST}:${MOCK_PORT}`)
    const path = url.pathname

    // CORS not needed for same-origin rewrite; keep simple JSON API
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

async function main() {
  const mockFree = await portFree(MOCK_HOST, MOCK_PORT)
  if (!mockFree) {
    console.error(`[preview:v2] Port ${MOCK_PORT} already occupied. Aborting.`)
    process.exit(1)
  }
  const nextFree = await portFree(NEXT_HOST, NEXT_PORT)
  if (!nextFree) {
    // also try 127.0.0.1
    const nextFreeLocal = await portFree("127.0.0.1", NEXT_PORT)
    if (!nextFreeLocal) {
      console.error(`[preview:v2] Port ${NEXT_PORT} already occupied. Aborting.`)
      process.exit(1)
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
    NEXT_DIST_DIR: ".next-v2-preview",
    DEV_API_REWRITE_BASE_URL: `http://${MOCK_HOST}:${MOCK_PORT}`,
  }

  const next = spawn(
    "pnpm",
    ["exec", "next", "dev", "--hostname", NEXT_HOST, "--port", String(NEXT_PORT)],
    {
      cwd: ROOT,
      env,
      stdio: "inherit",
    },
  )

  let shuttingDown = false
  function shutdown(code = 0) {
    if (shuttingDown) return
    shuttingDown = true
    console.log("[preview:v2] Shutting down...")
    try {
      next.kill("SIGTERM")
    } catch {
      /* ignore */
    }
    try {
      mock.close()
    } catch {
      /* ignore */
    }
    setTimeout(() => process.exit(code), 300)
  }

  process.on("SIGINT", () => shutdown(0))
  process.on("SIGTERM", () => shutdown(0))
  next.on("exit", (code) => {
    if (!shuttingDown) {
      console.error(`[preview:v2] Next exited with code ${code}`)
      shutdown(code ?? 1)
    }
  })

  console.log("[preview:v2] http://127.0.0.1:3003/day/2026-07-08")
  console.log("[preview:v2] TEST-ONLY mock visual preview. Do not use for production.")
}

main().catch((err) => {
  console.error("[preview:v2] Fatal:", err)
  process.exit(1)
})
