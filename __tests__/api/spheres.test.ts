// ############################################################################
// AI_HEADER: TEST_API_SPHERES — sphere page API client contract.
// ROLE: Proves typed errors and zod validation of the /api/spheres/{key} client.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-API-SPHERES
// purpose: Exercise fetchSpherePage success, HTTP, network and invalid paths.
// owns:
//   - __tests__/api/spheres.test.ts
// inputs: mock instrumentedFetch responses and generated sphere page payloads.
// outputs: assertions on payload passthrough and SpherePageApiError typing.
// dependencies: lib/api/spheres, instrumentedFetch mock.
// side_effects: none.
// emitted_logs: none.
// invariants: no real network calls.
// failure_policy: pytest-style assertion failure on contract drift.
// END_MODULE_CONTRACT: M-TEST-API-SPHERES

// START_MODULE_MAP: M-TEST-API-SPHERES
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - SUCCESS: payload passthrough and request shape.
//   - ERRORS: http/network/invalid typed failures.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-API-SPHERES

import { describe, expect, it, vi, beforeEach } from "vitest"

const { mockInstrumentedFetch } = vi.hoisted(() => ({
  mockInstrumentedFetch: vi.fn(),
}))

vi.mock("@/lib/log/instrumented-fetch", () => ({
  instrumentedFetch: mockInstrumentedFetch,
}))

import { fetchSpherePage, SpherePageApiError } from "@/lib/api/spheres"

beforeEach(() => {
  mockInstrumentedFetch.mockReset()
})

const validPayload = {
  sphere: "work",
  birthTimeMode: "exact",
  housesAvailable: true,
  natal: {
    state: "ready",
    paragraphs: [{ text: "Солнце поддерживает работу.", sourceFactIds: ["natal:planet:SUN"] }],
  },
  period: [
    {
      id: "p1",
      technique: "firdar_major",
      title: "Большой фирдар Солнца",
      activeFrom: "2024-05-01",
      activeUntil: "2031-05-01",
    },
  ],
  periodIdentity: "a".repeat(32),
  periodUnavailable: false,
}

// START_BLOCK: SUCCESS
describe("fetchSpherePage", () => {
  it("returns the validated payload and sends the expected request", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validPayload), { status: 200 }),
    )

    const payload = await fetchSpherePage("work")

    expect(payload.sphere).toBe("work")
    expect(payload.period).toHaveLength(1)
    const call = mockInstrumentedFetch.mock.calls[0][0]
    expect(call.url).toBe("/api/spheres/work")
    expect(call.init.credentials).toBe("include")
    expect(call.operation).toBe("spheres.page")
  })

  it("encodes the sphere key in the URL", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validPayload), { status: 200 }),
    )

    await fetchSpherePage("money health")

    expect(mockInstrumentedFetch.mock.calls[0][0].url).toBe(
      `/api/spheres/${encodeURIComponent("money health")}`,
    )
  })
// END_BLOCK: SUCCESS

// START_BLOCK: ERRORS
  it("throws typed http error with backend code for 403", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ detail: { code: "ACCESS_REQUIRED" } }), { status: 403 }),
    )

    const failure = await fetchSpherePage("work").catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(SpherePageApiError)
    expect((failure as SpherePageApiError).kind).toBe("http")
    expect((failure as SpherePageApiError).status).toBe(403)
    expect((failure as SpherePageApiError).code).toBe("ACCESS_REQUIRED")
  })

  it("wraps transport failures into typed network error", async () => {
    mockInstrumentedFetch.mockRejectedValueOnce(new TypeError("fetch failed"))

    const failure = await fetchSpherePage("work").catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(SpherePageApiError)
    expect((failure as SpherePageApiError).kind).toBe("network")
    expect((failure as SpherePageApiError).status).toBe(0)
  })

  it("falls back to the default message for http errors without details", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response("not-json", { status: 500 }),
    )

    const failure = await fetchSpherePage("work").catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(SpherePageApiError)
    expect((failure as SpherePageApiError).kind).toBe("http")
    expect((failure as SpherePageApiError).status).toBe(500)
  })

  it("keeps a wrapped SpherePageApiError untouched", async () => {
    mockInstrumentedFetch.mockRejectedValueOnce(
      new SpherePageApiError("boom", "http", 502, "UPSTREAM"),
    )

    const failure = await fetchSpherePage("work").catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(SpherePageApiError)
    expect((failure as SpherePageApiError).status).toBe(502)
    expect((failure as SpherePageApiError).code).toBe("UPSTREAM")
  })

  it("rejects an invalid payload as typed invalid error", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify({ sphere: "work" }), { status: 200 }),
    )

    const failure = await fetchSpherePage("work").catch((error: unknown) => error)

    expect(failure).toBeInstanceOf(SpherePageApiError)
    expect((failure as SpherePageApiError).kind).toBe("invalid")
  })

  it("passes the abort signal through to the transport", async () => {
    mockInstrumentedFetch.mockResolvedValueOnce(
      new Response(JSON.stringify(validPayload), { status: 200 }),
    )
    const controller = new AbortController()

    await fetchSpherePage("work", controller.signal)

    expect(mockInstrumentedFetch.mock.calls[0][0].init.signal).toBe(controller.signal)
  })
})
// END_BLOCK: ERRORS
