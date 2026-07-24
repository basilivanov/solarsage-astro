// ############################################################################
// AI_HEADER: MODULE_TESTS_INSTRUMENTED_FETCH
// ROLE: Unit tests for instrumentedFetch (Slice 02 & Slice 20)
// DEPENDENCIES: vitest, lib/log/instrumented-fetch
// GRACE_ANCHORS: [INSTRUMENTED_FETCH_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-INSTRUMENTED-FETCH
// purpose: Validate safe correlation ID adoption/sanitization, path route context vs http route_template, responseContract validation, and error classification in instrumentedFetch.
// owns:
//   - __tests__/lib/instrumented-fetch.test.ts
// inputs: mock fetch, RequestInit and responseContract options
// outputs: Vitest assertion results
// dependencies:
//   - M-LOG-INSTRUMENTED-FETCH (instrumentedFetch)
//   - M-LOG-FRONTEND (logEvent, getCorrelationId, setCorrelationId mocks)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-INSTRUMENTED-FETCH

// START_MODULE_MAP: M-TESTS-INSTRUMENTED-FETCH
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - CORRELATION_TESTS: test safe caller correlation adoption, unsafe header replacement, and response header filtering
//   - ROUTE_CONTEXT_TESTS: test path route in capture context vs GET route_template in http meta
//   - LIFECYCLE_TESTS: test fetch_started, fetch_succeeded, fetch_failed events and contract validation
// owned_tests:
//   - __tests__/lib/instrumented-fetch.test.ts
// END_MODULE_MAP: M-TESTS-INSTRUMENTED-FETCH

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

let currentCorrelationId: string | null = null

const { mockLogEvent, mockCaptureError, mockSetCorrelationId } = vi.hoisted(() => ({
  mockLogEvent: vi.fn(),
  mockCaptureError: vi.fn(),
  mockSetCorrelationId: vi.fn((id: string) => { currentCorrelationId = id }),
}))

vi.mock("@/lib/log/index", () => ({
  logEvent: mockLogEvent,
  getCorrelationId: () => currentCorrelationId,
  setCorrelationId: mockSetCorrelationId,
}))

vi.mock("@/lib/log/capture-error", async (importOriginal) => {
  const actual = await importOriginal<typeof import("@/lib/log/capture-error")>()
  return {
    ...actual,
    captureFrontendError: mockCaptureError,
  }
})

import { instrumentedFetch, isApiLogPath } from "@/lib/log/instrumented-fetch"

describe("instrumentedFetch — Slice 02 & Slice 20 Safety & Correlation", () => {
  beforeEach(() => {
    currentCorrelationId = null
    mockLogEvent.mockClear()
    mockCaptureError.mockClear()
    mockSetCorrelationId.mockClear()
  })

  afterEach(() => {
    currentCorrelationId = null
    vi.restoreAllMocks()
  })

  it("adopts safe caller correlation ID, echoes safe response correlation header, and passes path route context vs http route_template", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "Content-Type": "application/json",
          "X-Correlation-Id": "safe-server-corr-999",
        },
      })
    )

    const res = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24?secret_token=12345",
      init: {
        headers: {
          "X-Correlation-Id": "safe-caller-corr-123",
          Authorization: "Bearer secret_jwt",
        },
      },
      fetchImpl: mockFetch,
    })

    expect(res.status).toBe(200)

    // Caller safe correlation ID adopted
    expect(mockSetCorrelationId).toHaveBeenCalledWith("safe-caller-corr-123")
    // Safe response correlation ID adopted
    expect(mockSetCorrelationId).toHaveBeenCalledWith("safe-server-corr-999")

    // Request headers contains exact single X-Correlation-Id
    expect(mockFetch).toHaveBeenCalledWith(
      "/api/day/2026-07-24?secret_token=12345",
      expect.objectContaining({
        headers: expect.objectContaining({
          "X-Correlation-Id": "safe-caller-corr-123",
        }),
      })
    )

    // Check exact ui.fetch_started payload and http meta
    expect(mockLogEvent).toHaveBeenCalledWith(
      "ui.fetch_started",
      { route: "GET /api/day/{date}", method: "GET" },
      expect.objectContaining({
        phase: "request",
        operation_id: expect.any(String),
        http: { method: "GET", route_template: "GET /api/day/{date}" },
      })
    )

    const allLogCalls = JSON.stringify(mockLogEvent.mock.calls)
    expect(allLogCalls).not.toContain("secret_token")
    expect(allLogCalls).not.toContain("secret_jwt")
  })

  it("replaces unsafe caller correlation header with minted safe ID and ignores unsafe response correlation header", async () => {
    const mockFetch = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: true }), {
        status: 200,
        headers: {
          "X-Correlation-Id": "unsafe_response_bearer_token@secret.com",
        },
      })
    )

    const res = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      init: {
        headers: {
          "x-correlation-id": "unsafe_caller_bearer_token@secret.com",
        },
      },
      fetchImpl: mockFetch,
    })

    expect(res.status).toBe(200)

    // Unsafe caller correlation was NOT set via setCorrelationId
    expect(mockSetCorrelationId).not.toHaveBeenCalledWith("unsafe_caller_bearer_token@secret.com")
    // Unsafe response correlation was NOT adopted via setCorrelationId
    expect(mockSetCorrelationId).not.toHaveBeenCalledWith("unsafe_response_bearer_token@secret.com")

    // Outgoing request header contains minted safe ID (UUID)
    const outgoingHeaders = mockFetch.mock.calls[0][1].headers
    expect(outgoingHeaders["X-Correlation-Id"]).toBeDefined()
    expect(outgoingHeaders["x-correlation-id"]).toBeUndefined()
    expect(outgoingHeaders["X-Correlation-Id"]).not.toContain("unsafe")

    // Unsafe header is nowhere in log calls
    const allLogCalls = JSON.stringify(mockLogEvent.mock.calls)
    expect(allLogCalls).not.toContain("unsafe_caller")
    expect(allLogCalls).not.toContain("unsafe_response")
  })

  it("passes path-only template to captureFrontendError context route and full method template to http.route_template", async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response("Server Error", { status: 500 }))

    const res = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      fetchImpl: mockFetch,
    })

    expect(res.status).toBe(500)

    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.api_request_failed",
        route: "/api/day/{date}", // path template WITHOUT method prefix!
        http: { method: "GET", route_template: "GET /api/day/{date}", status: 500 }, // full template WITH method!
      })
    )
  })

  it("bypasses /api/_log only if pathname is exactly /api/_log, NOT query string", async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response(JSON.stringify({ shipped: true }), { status: 200 }))

    const res1 = await instrumentedFetch({
      operation: "log.ship",
      routeTemplate: "POST /api/_log",
      url: "/api/_log?foo=bar",
      fetchImpl: mockFetch,
    })

    expect(res1.status).toBe(200)
    expect(mockLogEvent).not.toHaveBeenCalled()

    mockFetch.mockClear()
    mockLogEvent.mockClear()

    const res2 = await instrumentedFetch({
      operation: "search.query",
      routeTemplate: "GET /api/search",
      url: "/api/search?q=/api/_log",
      fetchImpl: mockFetch,
    })

    expect(res2.status).toBe(200)
    expect(mockLogEvent).toHaveBeenCalledWith("ui.fetch_started", expect.any(Object), expect.any(Object))
  })

  it("isApiLogPath correctly tests pathname vs query string", () => {
    expect(isApiLogPath("/api/_log")).toBe(true)
    expect(isApiLogPath("/api/_log?q=1")).toBe(true)
    expect(isApiLogPath("https://example.com/api/_log#hash")).toBe(true)
    expect(isApiLogPath("/api/search?q=/api/_log")).toBe(false)
    expect(isApiLogPath("/api/other")).toBe(false)
  })

  it("handles HTTP 500 error classification and logging", async () => {
    const mockFetch = vi.fn().mockResolvedValue(new Response("Internal Error", { status: 500 }))

    const res = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      fetchImpl: mockFetch,
    })

    expect(res.status).toBe(500)
    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.api_request_failed",
        reasonCode: "http",
        phase: "failure",
      })
    )
    expect(mockLogEvent).toHaveBeenCalledWith(
      "ui.fetch_failed",
      { route: "GET /api/day/{date}", method: "GET", status: 500 },
      expect.objectContaining({ phase: "failure" })
    )
  })

  it("handles network error rethrow with error level", async () => {
    const mockFetch = vi.fn().mockRejectedValue(new TypeError("Failed to fetch"))

    await expect(
      instrumentedFetch({
        operation: "today.load",
        routeTemplate: "GET /api/day/{date}",
        url: "/api/day/2026-07-24",
        fetchImpl: mockFetch,
      })
    ).rejects.toThrow("Failed to fetch")

    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(TypeError),
      expect.objectContaining({
        reasonCode: "network",
        level: "error",
      })
    )
  })

  it("handles timeout error rethrow and timer cleanup", async () => {
    const mockFetch = vi.fn().mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) => {
        init.signal.addEventListener("abort", () => {
          reject(new DOMException("The operation was aborted", "AbortError"))
        })
      })
    })

    await expect(
      instrumentedFetch({
        operation: "today.load",
        routeTemplate: "GET /api/day/{date}",
        url: "/api/day/2026-07-24",
        timeoutMs: 20,
        fetchImpl: mockFetch,
      })
    ).rejects.toThrow()

    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        reasonCode: "timeout",
        level: "error",
      })
    )
  })

  it("handles external abort with warn level and listener cleanup", async () => {
    const abortController = new AbortController()

    const mockFetch = vi.fn().mockImplementation((_url, init) => {
      return new Promise((_resolve, reject) => {
        init.signal.addEventListener("abort", () => {
          reject(new DOMException("Aborted", "AbortError"))
        })
      })
    })

    const promise = instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      init: { signal: abortController.signal },
      fetchImpl: mockFetch,
    })

    abortController.abort()

    await expect(promise).rejects.toThrow()

    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.anything(),
      expect.objectContaining({
        reasonCode: "aborted",
        level: "warn",
      })
    )
  })

  it("validates response contract without consuming original response (invalid schema, thrown validator, invalid JSON)", async () => {
    // Case 1: Invalid schema
    const mockFetch1 = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ ok: false, missingKey: null }), { status: 200 })
    )

    const res1 = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      fetchImpl: mockFetch1,
      responseContract: {
        contractName: "DayResponse",
        contractVersion: "v1",
        validate: () => ({ valid: false, missingFields: ["day_summary"], shapeHash: "abc12345" }),
      },
    })

    expect(res1.status).toBe(200)
    const body1 = await res1.json()
    expect(body1).toEqual({ ok: false, missingKey: null })

    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.api_response_invalid",
        source: "contract",
        contractName: "DayResponse",
        missingFields: ["day_summary"],
        phase: "contract-validation",
      })
    )

    // Case 2: Thrown validator
    mockCaptureError.mockClear()
    const mockFetch2 = vi.fn().mockResolvedValue(
      new Response(JSON.stringify({ data: 123 }), { status: 200 })
    )

    const res2 = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      fetchImpl: mockFetch2,
      responseContract: {
        contractName: "DayResponse",
        contractVersion: "v1",
        validate: () => { throw new Error("Validation exception") },
      },
    })

    expect(res2.status).toBe(200)
    const body2 = await res2.json()
    expect(body2).toEqual({ data: 123 })
    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.api_response_invalid",
        contractName: "DayResponse",
      })
    )

    // Case 3: Invalid JSON body
    mockCaptureError.mockClear()
    const mockFetch3 = vi.fn().mockResolvedValue(
      new Response("Not HTML or JSON", { status: 200 })
    )

    const res3 = await instrumentedFetch({
      operation: "today.load",
      routeTemplate: "GET /api/day/{date}",
      url: "/api/day/2026-07-24",
      fetchImpl: mockFetch3,
      responseContract: {
        contractName: "DayResponse",
        contractVersion: "v1",
        validate: () => ({ valid: true }),
      },
    })

    expect(res3.status).toBe(200)
    const text3 = await res3.text()
    expect(text3).toBe("Not HTML or JSON")
    expect(mockCaptureError).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.api_response_invalid",
        reasonCode: "invalid_json",
      })
    )
  })
})
