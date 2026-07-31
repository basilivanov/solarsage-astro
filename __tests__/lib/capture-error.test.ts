// ############################################################################
// AI_HEADER: TEST_LOG_CAPTURE_ERROR — frontend error capture sanitizers.
// ROLE: Proves route sanitization and error normalization branches.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-LOG-CAPTURE-ERROR
// purpose: Exercise sanitizeRoute, sanitizeRouteTemplate and
//   normalizeFrontendError branch matrix.
// owns:
//   - __tests__/lib/capture-error.test.ts
// inputs: raw routes, templates and error shapes.
// outputs: sanitized strings and structured error assertions.
// dependencies: lib/log/capture-error.
// side_effects: none.
// emitted_logs: none.
// invariants: secrets, tokens and identifiers are always masked.
// failure_policy: assertion failure on sanitizer drift.
// END_MODULE_CONTRACT: M-TEST-LOG-CAPTURE-ERROR

// START_MODULE_MAP: M-TEST-LOG-CAPTURE-ERROR
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - ROUTE: segment sanitizer matrix.
//   - TEMPLATE: method prefix and placeholder handling.
//   - NORMALIZE: error kind/code normalization.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-LOG-CAPTURE-ERROR

import { describe, expect, it } from "vitest"

import {
  normalizeFrontendError,
  sanitizeRoute,
  sanitizeRouteTemplate,
} from "@/lib/log/capture-error"

// START_BLOCK: ROUTE
describe("sanitizeRoute", () => {
  it("returns undefined for missing or non-string input", () => {
    expect(sanitizeRoute()).toBeUndefined()
    expect(sanitizeRoute("")).toBeUndefined()
    expect(sanitizeRoute(42 as never)).toBeUndefined()
  })

  it("keeps safe placeholders and clean static segments", () => {
    expect(sanitizeRoute("/api/day/{date}/retry")).toBe("/api/day/{date}/retry")
    expect(sanitizeRoute("/api/spheres/work")).toBe("/api/spheres/work")
  })

  it("masks UUID, date and numeric segments", () => {
    expect(
      sanitizeRoute("/api/day/snapshots/123e4567-e89b-42d3-a456-426614174000/spheres/work"),
    ).toBe("/api/day/snapshots/:id/spheres/work")
    expect(sanitizeRoute("/api/day/2026-07-31")).toBe("/api/day/:date")
    expect(sanitizeRoute("/api/users/991001")).toBe("/api/users/:id")
  })

  it("masks secret-like, percent-encoded, @ and space segments", () => {
    expect(sanitizeRoute("/api/auth/abc%20def")).toBe("/api/auth/:id")
    expect(sanitizeRoute("/api/users/user@example.com")).toBe("/api/users/:id")
    expect(sanitizeRoute("/api/x/my token")).toBe("/api/x/:id")
    expect(sanitizeRoute("/api/x/api_key_123")).toBe("/api/x/:id")
  })

  it("masks overlong and unclean segments and strips query/hash", () => {
    expect(sanitizeRoute("/api/x/abcdefghijklmnopqrstuvwxyz")).toBe("/api/x/:id")
    expect(sanitizeRoute("/api/x/ok-segment?secret=1#frag")).toBe("/api/x/ok-segment")
  })
})
// END_BLOCK: ROUTE

// START_BLOCK: TEMPLATE
describe("sanitizeRouteTemplate", () => {
  it("returns undefined for missing or blank input", () => {
    expect(sanitizeRouteTemplate()).toBeUndefined()
    expect(sanitizeRouteTemplate("   ")).toBeUndefined()
  })

  it("uppercases an HTTP method prefix and sanitizes the path", () => {
    expect(sanitizeRouteTemplate("get /api/day/2026-07-31")).toBe(
      "GET /api/day/:date",
    )
  })

  it("handles templates without a method prefix", () => {
    expect(sanitizeRouteTemplate("/api/spheres/work")).toBe("/api/spheres/work")
  })
})
// END_BLOCK: TEMPLATE

// START_BLOCK: NORMALIZE
describe("normalizeFrontendError", () => {
  it("keeps a safe Error name and uppercase code", () => {
    const error = new Error("boom") as Error & { code?: string }
    error.name = "TypedError"
    error.code = "ACCESS_REQUIRED"

    const normalized = normalizeFrontendError(error, "caught", true)

    expect(normalized.kind).toBe("TypedError")
    expect(normalized.code).toBe("ACCESS_REQUIRED")
    expect(normalized.retryable).toBe(true)
    expect(normalized.source).toBe("caught")
    expect(normalized.fingerprint).toBeTruthy()
  })

  it("falls back to Error for unsafe kind names and drops unsafe codes", () => {
    const error = new Error("x")
    ;(error as { code?: string }).code = "not safe!"
    error.name = "weird name with spaces"

    const normalized = normalizeFrontendError(error)

    expect(normalized.kind).toBe("Error")
    expect(normalized.code).toBeUndefined()
  })

  it("maps string and object rejections to stable kinds", () => {
    expect(normalizeFrontendError("nope").kind).toBe("StringRejection")

    const objectKind = normalizeFrontendError({ name: "CustomThing" }).kind
    expect(objectKind).toBe("CustomThing")

    const unsafeObject = normalizeFrontendError({ name: "has spaces" }).kind
    expect(unsafeObject).toBe("ObjectRejection")
  })

  it("produces different fingerprints for different errors", () => {
    const a = normalizeFrontendError(new Error("a"))
    const b = normalizeFrontendError(new Error("b"))
    expect(a.fingerprint).not.toBe(b.fingerprint)
  })
})
// END_BLOCK: NORMALIZE
