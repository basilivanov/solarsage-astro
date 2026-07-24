// ############################################################################
// AI_HEADER: MODULE_TESTS_APP_ERROR_BOUNDARIES
// ROLE: Unit and DOM acceptance tests for app/error.tsx and app/global-error.tsx
// DEPENDENCIES: vitest, @testing-library/react, app/error, app/global-error
// GRACE_ANCHORS: [APP_ERROR_BOUNDARIES_TESTS]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-TESTS-APP-ERROR-BOUNDARIES
// purpose: Validate DOM accessibility attributes, privacy boundaries, capture events, and retry callbacks for Next.js error boundaries.
// owns:
//   - __tests__/app/error-boundaries.test.tsx
// inputs: mock errors, reset callbacks, testing-library harness
// outputs: Vitest test execution assertions
// dependencies:
//   - M-APP-ERROR (AppError)
//   - M-APP-GLOBAL-ERROR (GlobalError)
//   - M-LOG-CAPTURE-ERROR (captureFrontendError mock)
// side_effects: none (test harness)
// failure_policy: raise assertions
// END_MODULE_CONTRACT: M-TESTS-APP-ERROR-BOUNDARIES

// START_MODULE_MAP: M-TESTS-APP-ERROR-BOUNDARIES
// public_entrypoints:
//   - none (test suite)
// semantic_blocks:
//   - APP_ERROR_TESTS: app/error.tsx acceptance tests
//   - GLOBAL_ERROR_TESTS: app/global-error.tsx acceptance tests
// owned_tests:
//   - __tests__/app/error-boundaries.test.tsx
// END_MODULE_MAP: M-TESTS-APP-ERROR-BOUNDARIES

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest"
import { render, screen, fireEvent } from "@testing-library/react"
import React from "react"

const { mockCapture } = vi.hoisted(() => ({
  mockCapture: vi.fn(),
}))

vi.mock("@/lib/log/capture-error", () => ({
  captureFrontendError: mockCapture,
}))

import AppError from "@/app/error"
import GlobalError from "@/app/global-error"

describe("App & Global Error Boundaries — Acceptance", () => {
  beforeEach(() => {
    mockCapture.mockClear()
    window.history.replaceState({}, "", "/readings/election")
  })

  afterEach(() => {
    window.history.replaceState({}, "", "/")
  })

  describe("AppError (app/error.tsx)", () => {
    it("renders fallback UI with role=alert, data-state=error, data-testid=app-error-boundary and accessible retry button", () => {
      const err = new Error("Component crashed with sensitive_db_password_123")
      const mockReset = vi.fn()

      render(<AppError error={err} reset={mockReset} />)

      const boundary = screen.getByTestId("app-error-boundary")
      expect(boundary).toBeDefined()
      expect(boundary.getAttribute("role")).toBe("alert")
      expect(boundary.getAttribute("data-state")).toBe("error")

      const button = screen.getByRole("button", { name: "Попробовать снова" })
      expect(button).toBeDefined()
    })

    it("does NOT leak raw error.message or digest into the DOM", () => {
      const err = Object.assign(new Error("SECRET_INTERNAL_DATABASE_URL"), {
        digest: "SECRET_DIGEST_9999",
      })

      const { container } = render(<AppError error={err} reset={vi.fn()} />)

      expect(container.textContent).not.toContain("SECRET_INTERNAL_DATABASE_URL")
      expect(container.textContent).not.toContain("SECRET_DIGEST_9999")
    })

    it("triggers captureFrontendError on mount with resetAttempted=false", () => {
      const err = new Error("Render error")
      render(<AppError error={err} reset={vi.fn()} />)

      expect(mockCapture).toHaveBeenCalledWith(
        err,
        expect.objectContaining({
          event: "frontend.render_failed",
          source: "react-boundary",
          boundary: "app-route",
          componentArea: "route-tree",
          resetAttempted: false,
          slice: "W-FRONTEND",
          module: "M-APP-ERROR",
          block: "ERROR_BOUNDARY_UI",
        })
      )
    })

    it("clicking retry button captures error with resetAttempted=true and force=true, then calls reset once", () => {
      const err = new Error("Render error")
      const mockReset = vi.fn()

      render(<AppError error={err} reset={mockReset} />)
      mockCapture.mockClear()

      const button = screen.getByRole("button", { name: "Попробовать снова" })
      fireEvent.click(button)

      expect(mockCapture).toHaveBeenCalledWith(
        err,
        expect.objectContaining({
          event: "frontend.render_failed",
          source: "react-boundary",
          boundary: "app-route",
          componentArea: "route-tree",
          resetAttempted: true,
          force: true,
          slice: "W-FRONTEND",
          module: "M-APP-ERROR",
          block: "ERROR_BOUNDARY_UI",
        })
      )

      expect(mockReset).toHaveBeenCalledTimes(1)
    })
  })

  describe("GlobalError (app/global-error.tsx)", () => {
    it("renders root document <html lang='ru'><body> with role=alert, data-state=error, data-testid=global-error-boundary in isolated Document", () => {
      const err = new Error("Root crash")
      const mockReset = vi.fn()

      const doc = document.implementation.createHTMLDocument("global-error-test")
      render(<GlobalError error={err} reset={mockReset} />, { container: doc })

      expect(doc.documentElement.getAttribute("lang")).toBe("ru")
      expect(doc.body).toBeDefined()

      const boundary = doc.body.querySelector('[data-testid="global-error-boundary"]')
      expect(boundary).not.toBeNull()
      expect(boundary?.getAttribute("role")).toBe("alert")
      expect(boundary?.getAttribute("data-state")).toBe("error")

      const button = boundary?.querySelector("button")
      expect(button).not.toBeNull()
      expect(button?.textContent?.trim()).toBe("Попробовать снова")
    })

    it("does NOT leak raw error.message or digest into the DOM", () => {
      const err = Object.assign(new Error("RAW_FATAL_PANIC"), {
        digest: "DIGEST_8888",
      })

      const doc = document.implementation.createHTMLDocument("global-error-test")
      render(<GlobalError error={err} reset={vi.fn()} />, { container: doc })

      expect(doc.documentElement.textContent).not.toContain("RAW_FATAL_PANIC")
      expect(doc.documentElement.textContent).not.toContain("DIGEST_8888")
    })

    it("triggers captureFrontendError on mount with resetAttempted=false", () => {
      const err = new Error("Root layout crash")
      const doc = document.implementation.createHTMLDocument("global-error-test")

      render(<GlobalError error={err} reset={vi.fn()} />, { container: doc })

      expect(mockCapture).toHaveBeenCalledWith(
        err,
        expect.objectContaining({
          event: "frontend.render_failed",
          source: "react-boundary",
          boundary: "global-root",
          componentArea: "root-layout",
          resetAttempted: false,
          slice: "W-FRONTEND",
          module: "M-APP-GLOBAL-ERROR",
          block: "GLOBAL_ERROR_BOUNDARY_UI",
        })
      )
    })

    it("clicking retry button captures error with resetAttempted=true and force=true, then calls reset once", () => {
      const err = new Error("Root layout crash")
      const mockReset = vi.fn()

      const doc = document.implementation.createHTMLDocument("global-error-test")
      render(<GlobalError error={err} reset={mockReset} />, { container: doc })
      mockCapture.mockClear()

      const button = doc.body.querySelector("button")!
      expect(button).not.toBeNull()
      button.click()

      expect(mockCapture).toHaveBeenCalledWith(
        err,
        expect.objectContaining({
          event: "frontend.render_failed",
          source: "react-boundary",
          boundary: "global-root",
          componentArea: "root-layout",
          resetAttempted: true,
          force: true,
          slice: "W-FRONTEND",
          module: "M-APP-GLOBAL-ERROR",
          block: "GLOBAL_ERROR_BOUNDARY_UI",
        })
      )

      expect(mockReset).toHaveBeenCalledTimes(1)
    })
  })
})
