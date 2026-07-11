// ############################################################################
// AI_HEADER: TEST_DEV_TIMING_FIXTURE_ROUTE — test suite for dev fixture route guard
// ROLE: Verifies that GET endpoint for dev fixture rejects non-local/non-dev requests.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-DEV-TIMING-FIXTURE-ROUTE
// purpose: Test that /api/dev-fixtures/three-horizon-timing route guards are active.
// owns:
//   - __tests__/api/dev-timing-fixture-route.test.ts
// inputs: HTTP mock GET requests
// outputs: vitest assertions
// dependencies: app/api/dev-fixtures/three-horizon-timing/route.ts
// side_effects: none
// emitted_logs: none
// invariants: только development + local direct request получает 200
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-DEV-TIMING-FIXTURE-ROUTE

// START_MODULE_MAP: M-TEST-DEV-TIMING-FIXTURE-ROUTE
// public_entrypoints:
//   - GET (tested route handler)
// semantic_blocks:
//   - ROUTE_GUARD_TESTS: validates local host, NODE_ENV, and proxy-origin header constraints
// owned_tests:
//   - __tests__/api/dev-timing-fixture-route.test.ts
// END_MODULE_MAP: M-TEST-DEV-TIMING-FIXTURE-ROUTE

import { afterEach, describe, expect, it, vi } from "vitest"
import { GET } from "@/app/api/dev-fixtures/three-horizon-timing/route"

afterEach(() => {
  vi.unstubAllEnvs()
})

function request(headers: HeadersInit = {}): Request {
  return new Request("http://127.0.0.1:3003/api/dev-fixtures/three-horizon-timing", {
    headers: { host: "127.0.0.1:3003", ...headers },
  })
}

describe("dev timing fixture route guard", () => {
  it("serves the fixture only to a direct local development request", async () => {
    vi.stubEnv("NODE_ENV", "development")

    const response = await GET(request())

    expect(response.status).toBe(200)
    await expect(response.json()).resolves.toMatchObject({ date: "2026-07-08" })
  })

  it("rejects production before reading the fixture", async () => {
    vi.stubEnv("NODE_ENV", "production")

    expect((await GET(request())).status).not.toBe(200)
  })

  it("rejects a public Host header", async () => {
    vi.stubEnv("NODE_ENV", "development")

    expect((await GET(request({ host: "preview.example.test" }))).status).not.toBe(200)
  })

  it("rejects unsafe proxy-origin headers", async () => {
    vi.stubEnv("NODE_ENV", "development")

    expect((await GET(request({ "x-forwarded-host": "preview.example.test" }))).status).not.toBe(200)
  })
})
