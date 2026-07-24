// ############################################################################
// AI_HEADER: MODULE_TESTS_FRONTEND_ERROR_CAPTURE
// ROLE: Unit and lifecycle acceptance tests for FrontendErrorCapture component
// DEPENDENCIES: vitest, @testing-library/react, components/telemetry/frontend-error-capture
// GRACE_ANCHORS: [FRONTEND_ERROR_CAPTURE_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-FRONTEND-ERROR-CAPTURE
// purpose: Validate DOM render, listener lifecycle identity, route isolation, and event mapping for FrontendErrorCapture.
// owns:
//   - __tests__/components/FrontendErrorCapture.test.tsx
// inputs: mock window events and React render harness
// outputs: Vitest test execution assertions
// dependencies:
//   - M-FRONTEND-ERROR-CAPTURE (FrontendErrorCapture)
//   - M-LOG-CAPTURE-ERROR (captureFrontendError mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-FRONTEND-ERROR-CAPTURE

// START_MODULE_MAP: M-TESTS-FRONTEND-ERROR-CAPTURE
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - LISTENER_LIFECYCLE: test listener identity and cleanup
//   - EVENT_MAPPING: test window.error and unhandledrejection capture
//   - ROUTE_ISOLATION: test pathname vs query/hash isolation
// owned_tests:
//   - __tests__/components/FrontendErrorCapture.test.tsx
// END_MODULE_MAP: M-TESTS-FRONTEND-ERROR-CAPTURE

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render } from "@testing-library/react"
import React from "react"

const { mockCapture } = vi.hoisted(() => ({
  mockCapture: vi.fn(),
}))

vi.mock("@/lib/log/capture-error", () => ({
  captureFrontendError: mockCapture,
}))

import { FrontendErrorCapture } from "@/components/telemetry/frontend-error-capture"

describe("FrontendErrorCapture — Acceptance", () => {
  beforeEach(() => {
    mockCapture.mockClear()
    window.history.replaceState({}, "", "/")
  })

  afterEach(() => {
    window.history.replaceState({}, "", "/")
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it("renders null and attaches exactly 1 error and 1 unhandledrejection handler on mount", () => {
    const addEventListenerSpy = vi.spyOn(window, "addEventListener")

    const { container } = render(<FrontendErrorCapture />)

    expect(container.firstChild).toBeNull()

    const errorCalls = addEventListenerSpy.mock.calls.filter(([event]) => event === "error")
    const rejectionCalls = addEventListenerSpy.mock.calls.filter(([event]) => event === "unhandledrejection")

    expect(errorCalls).toHaveLength(1)
    expect(rejectionCalls).toHaveLength(1)
  })

  it("removes the exact same function references on unmount", () => {
    const addEventListenerSpy = vi.spyOn(window, "addEventListener")
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener")

    const { unmount } = render(<FrontendErrorCapture />)

    const errorHandler = addEventListenerSpy.mock.calls.find(([event]) => event === "error")?.[1]
    const rejectionHandler = addEventListenerSpy.mock.calls.find(([event]) => event === "unhandledrejection")?.[1]

    expect(errorHandler).toBeDefined()
    expect(rejectionHandler).toBeDefined()

    unmount()

    expect(removeEventListenerSpy).toHaveBeenCalledWith("error", errorHandler)
    expect(removeEventListenerSpy).toHaveBeenCalledWith("unhandledrejection", rejectionHandler)
  })

  it("remounting cleans up old handlers and leaves no duplicate active handlers", () => {
    const addEventListenerSpy = vi.spyOn(window, "addEventListener")
    const removeEventListenerSpy = vi.spyOn(window, "removeEventListener")

    const { unmount: unmount1 } = render(<FrontendErrorCapture />)
    unmount1()

    const { unmount: unmount2 } = render(<FrontendErrorCapture />)

    const errorAddCalls = addEventListenerSpy.mock.calls.filter(([event]) => event === "error")
    const errorRemoveCalls = removeEventListenerSpy.mock.calls.filter(([event]) => event === "error")

    expect(errorAddCalls).toHaveLength(2)
    expect(errorRemoveCalls).toHaveLength(1)

    unmount2()
    expect(removeEventListenerSpy.mock.calls.filter(([event]) => event === "error")).toHaveLength(2)
  })

  it("captures window.error event with exact module/block and pathname route without query or hash", () => {
    window.history.replaceState({}, "", "/readings/natal?secret_key=12345#section-2")

    const mockFetch = vi.fn()
    vi.stubGlobal("fetch", mockFetch)

    render(<FrontendErrorCapture />)

    const err = new Error("Uncaught runtime exception")
    const errorEvent = new ErrorEvent("error", {
      error: err,
      message: "Uncaught runtime exception",
    })

    window.dispatchEvent(errorEvent)

    expect(mockCapture).toHaveBeenCalledWith(
      err,
      expect.objectContaining({
        event: "frontend.runtime_failed",
        source: "window.error",
        route: "/readings/natal",
        slice: "W-FRONTEND",
        module: "M-FRONTEND-RUNTIME",
        block: "GLOBAL_ERROR_HANDLER",
      })
    )

    expect(mockFetch).not.toHaveBeenCalled()
  })

  it("captures unhandledrejection event with exact module/block", () => {
    window.history.replaceState({}, "", "/horary?query=secret#tab")

    render(<FrontendErrorCapture />)

    const rejectionEvent = new Event("unhandledrejection") as any
    rejectionEvent.reason = new Error("Unhandled async rejection")

    window.dispatchEvent(rejectionEvent)

    expect(mockCapture).toHaveBeenCalledWith(
      expect.any(Error),
      expect.objectContaining({
        event: "frontend.promise_rejected",
        source: "unhandledrejection",
        route: "/horary",
        slice: "W-FRONTEND",
        module: "M-FRONTEND-RUNTIME",
        block: "GLOBAL_REJECTION_HANDLER",
      })
    )
  })
})
