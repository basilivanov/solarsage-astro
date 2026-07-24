// ############################################################################
// AI_HEADER: MODULE_TESTS_CAPTURE_ERROR
// ROLE: Unit tests for captureFrontendError, normalizeFrontendError and fingerprinting (Slice 01 & 20)
// DEPENDENCIES: vitest, lib/log/capture-error
// GRACE_ANCHORS: [CAPTURE_ERROR_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-CAPTURE-ERROR
// purpose: Validate error normalization, stack frame cleaning, fingerprint deduplication, route sanitization with placeholders, and top-level meta safety.
// owns:
//   - __tests__/lib/capture-error.test.ts
// inputs: mock shipper enqueue, error instances and rejection payloads
// outputs: Vitest assertion results
// dependencies:
//   - M-LOG-CAPTURE-ERROR (lib/log/capture-error)
//   - M-LOG-SHIPPER (getLogShipper mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-CAPTURE-ERROR

// START_MODULE_MAP: M-TESTS-CAPTURE-ERROR
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - NORMALIZATION_TESTS: test name/kind/code PII stripping and stack frame parsing
//   - ROUTE_SANITIZATION_TESTS: test route parameterization and placeholder preservation
//   - DEDUP_TESTS: test session fingerprint deduplication limits
//   - META_TESTS: test top-level meta envelope attributes and sanitization
// owned_tests:
//   - __tests__/lib/capture-error.test.ts
// END_MODULE_MAP: M-TESTS-CAPTURE-ERROR

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"

const { mockEnqueue } = vi.hoisted(() => ({
  mockEnqueue: vi.fn(),
}))

vi.mock("@/lib/log/shipper", () => ({
  getLogShipper: () => ({ enqueue: mockEnqueue }),
}))

import {
  captureFrontendError,
  normalizeFrontendError,
  sanitizeRoute,
  sanitizeRouteTemplate,
  resetFingerprintDeduplicationForTests,
} from "@/lib/log/capture-error"

describe("capture-error — Slice 01 & Slice 20 Privacy, Normalization & Route Placeholders", () => {
  beforeEach(() => {
    mockEnqueue.mockClear()
    resetFingerprintDeduplicationForTests()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    resetFingerprintDeduplicationForTests()
  })

  it("sanitises malicious name, kind, and code containing emails or tokens", () => {
    const err = new Error("Failed")
    err.name = "CustomError<user@example.com>"
    ;(err as any).code = "lowercase_secret_token"

    const normalized = normalizeFrontendError(err, "caught")

    expect(normalized.kind).toBe("Error")
    expect(normalized.code).toBeUndefined()
    expect(JSON.stringify(normalized)).not.toContain("user@example.com")
    expect(JSON.stringify(normalized)).not.toContain("lowercase_secret_token")

    // Valid uppercase code
    const err2 = new Error("Failed 2")
    ;(err2 as any).code = "NETWORK_ERROR_404"
    const normalized2 = normalizeFrontendError(err2, "caught")
    expect(normalized2.code).toBe("NETWORK_ERROR_404")
  })

  it("sanitises absolute path, origin, query/hash, unsafe segments and function names in stack frames", () => {
    const err = new Error("Crashed")
    err.stack = `Error: Crashed
    at safeFunc (https://astro.vasiliy-ivanov.ru/app/alice%40example.com/page.tsx?token=secret123#section:10:20)
    at /home/astro/work/solarsage-astro/lib/api/today.ts:45:10
    at /var/www/other/script.js:1:2`

    const normalized = normalizeFrontendError(err, "window.error")

    expect(normalized.stack_frames).toBeDefined()
    expect(normalized.stack_frames![0].file).toBe("app/:param/page.tsx")
    expect(normalized.stack_frames![0].function).toBe("safeFunc")
    expect(normalized.stack_frames![1].file).toBe("lib/api/today.ts:45:10")
    expect(normalized.stack_frames![2].file).toBe("script.js:1:2")

    const dumped = JSON.stringify(normalized)
    expect(dumped).not.toContain("token=secret123")
    expect(dumped).not.toContain("https://astro.vasiliy-ivanov.ru")
    expect(dumped).not.toContain("/home/astro/")
    expect(dumped).not.toContain("alice%40example.com")
  })

  it("caps stack frames to a maximum of 8 frames", () => {
    const err = new Error("Deep stack")
    const lines = ["Error: Deep stack"]
    for (let i = 1; i <= 15; i++) {
      lines.push(`    at func${i} (app/components/comp${i}.tsx:${i}:${i})`)
    }
    err.stack = lines.join("\n")

    const normalized = normalizeFrontendError(err, "react-boundary")
    expect(normalized.stack_frames).toHaveLength(8)
  })

  it("parameterizes dynamic/unsafe segments while preserving safe {placeholder} segments in sanitizeRoute", () => {
    const sanitizedUuid = sanitizeRoute("/readings/election/34cdf627-7ca2-4864-b3dd-42b96e0515f7?secret=1")
    expect(sanitizedUuid).toBe("/readings/election/:id")

    const sanitizedEmail = sanitizeRoute("/users/alice%40example.com")
    expect(sanitizedEmail).toBe("/users/:id")

    const sanitizedDate = sanitizeRoute("/api/day/2026-07-24#tab")
    expect(sanitizedDate).toBe("/api/day/:date")

    const sanitizedNum = sanitizeRoute("/users/12345/profile")
    expect(sanitizedNum).toBe("/users/:id/profile")

    // Slice 20 requirement: sanitizeRoute preserves safe {placeholder}
    const sanitizedPlaceholder = sanitizeRoute("/api/day/{date}")
    expect(sanitizedPlaceholder).toBe("/api/day/{date}")
  })

  it("tracks dedup independently across different operations, boundaries, or routes", () => {
    const err = new Error("Network error")

    // Capture 3 times under operation "today.load"
    for (let i = 0; i < 3; i++) {
      captureFrontendError(err, { operation: "today.load" })
    }
    expect(mockEnqueue).toHaveBeenCalledTimes(3)

    // 4th time under same operation is deduped
    captureFrontendError(err, { operation: "today.load" })
    expect(mockEnqueue).toHaveBeenCalledTimes(3)

    // Different operation "calendar.load" is NOT deduped
    captureFrontendError(err, { operation: "calendar.load" })
    expect(mockEnqueue).toHaveBeenCalledTimes(4)

    // Different route "/readings/election/:id" is NOT deduped
    captureFrontendError(err, { operation: "today.load", route: "/readings/election/123" })
    expect(mockEnqueue).toHaveBeenCalledTimes(5)
  })

  it("normalizes primitive or object rejections without dragging raw values into fingerprint or output", () => {
    const rawSecret = "user_pass_123456"
    const normalized = normalizeFrontendError(rawSecret, "unhandledrejection")

    expect(normalized.kind).toBe("StringRejection")
    expect(JSON.stringify(normalized)).not.toContain("user_pass_123456")

    const objSecret = { password: "secret_password_777", name: "MaliciousName<secret>" }
    const normalizedObj = normalizeFrontendError(objSecret, "unhandledrejection")
    expect(normalizedObj.kind).toBe("ObjectRejection")
    expect(JSON.stringify(normalizedObj)).not.toContain("secret_password_777")
  })

  it("sanitises and caps context metadata fields in payload and meta before shipping", () => {
    captureFrontendError(new Error("Test"), {
      operation: "operation_with_email_alice@example.com_and_secret",
      boundary: "safe_boundary",
      componentArea: "safeArea",
      reasonCode: "REASON_CODE_404",
      missingFields: ["field1", "field_with_email@example.com"],
      slice: "W-FRONTEND",
    })

    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.payload.operation).toBeUndefined()
    expect(env.payload.boundary).toBe("safe_boundary")
    expect(env.payload.component_area).toBe("safeArea")
    expect(env.payload.reason_code).toBe("REASON_CODE_404")
    expect(env.payload.missing_fields).toEqual(["field1"])
    expect(JSON.stringify(env)).not.toContain("alice@example.com")
  })

  it("Slice 02 regression: safe http/duration/phase/operation ID end up top-level in envelope", () => {
    captureFrontendError(new Error("Network fail"), {
      operation: "today.load",
      operation_id: "op-12345-uuid",
      phase: "failure",
      duration_ms: 120,
      http: { method: "GET", route_template: "/api/day/{date}", status: 500 },
      slice: "W-FRONTEND",
    })

    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]
    expect(env.operation_id).toBe("op-12345-uuid")
    expect(env.phase).toBe("failure")
    expect(env.duration_ms).toBe(120)
    expect(env.http).toEqual({ method: "GET", route_template: "/api/day/{date}", status: 500 })
  })

  it("Slice 02 regression: omits operation_id when not a safe instance ID and sanitises top-level http/duration_ms/phase", () => {
    mockEnqueue.mockClear()

    captureFrontendError(new Error("Fail without instance ID"), {
      operation: "today.load", // semantic label only, no operation_id!
      duration_ms: -50, // invalid negative duration
      http: { method: "INVALID_LONG_METHOD_NAME", route_template: "GET /users/alice%40example.com?secret=1", status: 9999 },
      phase: "invalid phase string with @ email",
    })

    expect(mockEnqueue).toHaveBeenCalledTimes(1)
    const env = mockEnqueue.mock.calls[0][0]

    expect(env.operation_id).toBeUndefined()
    expect(env.duration_ms).toBeUndefined()
    expect(env.phase).toBeUndefined()
    expect(env.http?.method).toBeUndefined()
    expect(env.http?.status).toBeUndefined()
    expect(env.http?.route_template).toBe("GET /users/:id")
  })

  it("Slice 02 regression: sanitizeRouteTemplate preserves HTTP METHOD and {placeholders}", () => {
    expect(sanitizeRouteTemplate("GET /api/day/{date}")).toBe("GET /api/day/{date}")
    expect(sanitizeRouteTemplate("POST /api/chat?token=secret#section")).toBe("POST /api/chat")
    expect(sanitizeRouteTemplate("GET /users/34cdf627-7ca2-4864-b3dd-42b96e0515f7/profile")).toBe("GET /users/:id/profile")
  })
})
