// ############################################################################
// AI_HEADER: MODULE_APP_ERROR
// ROLE: Route-tree error boundary for React/Next errors.
// DEPENDENCIES: lib/log/capture-error
// GRACE_ANCHORS: [APP_ERROR_BOUNDARY]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-APP-ERROR
// purpose: Next.js route-level error boundary component that logs render errors and presents a user fallback UI.
// owns:
//   - app/error.tsx
// inputs: error (Error & { digest?: string }), reset (() => void)
// outputs: TSX fallback UI with role="alert", data-testid="app-error-boundary", data-state="error"
// dependencies:
//   - M-LOG-CAPTURE-ERROR (captureFrontendError)
// side_effects:
//   - logs frontend.render_failed event on mount/error change
//   - logs frontend.render_failed event with reset_attempted=true on retry click
// emitted_logs: frontend.render_failed
// failure_policy:
//   - internal errors swallowed safely; fallback UI remains rendered
// END_MODULE_CONTRACT: M-APP-ERROR

// START_MODULE_MAP: M-APP-ERROR
// public_entrypoints:
//   - AppError (default)
// semantic_blocks:
//   - ERROR_BOUNDARY_UI: accessible fallback UI with reset button
// owned_tests:
//   - __tests__/app/error-boundaries.test.tsx
// END_MODULE_MAP: M-APP-ERROR

"use client"

import { useEffect } from "react"
import { captureFrontendError } from "@/lib/log/capture-error"

// START_BLOCK: ERROR_BOUNDARY_UI
export default function AppError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  // START_FUNCTION_CONTRACT: F-M-APP-ERROR.AppError
  // purpose: Next.js route-tree error boundary component rendering accessible fallback UI and logging errors.
  // inputs: error — Error instance, reset — callback function to attempt recovering
  // returns: JSX.Element
  // side_effects: logs frontend.render_failed via captureFrontendError
  // emitted_logs: frontend.render_failed
  // END_FUNCTION_CONTRACT: F-M-APP-ERROR.AppError
  const pathname = typeof window !== "undefined" ? window.location.pathname : ""

  useEffect(() => {
    captureFrontendError(error, {
      event: "frontend.render_failed",
      source: "react-boundary",
      route: pathname,
      boundary: "app-route",
      componentArea: "route-tree",
      resetAttempted: false,
      slice: "W-FRONTEND",
      module: "M-APP-ERROR",
      block: "ERROR_BOUNDARY_UI",
    })
  }, [error, pathname])

  const handleRetry = () => {
    captureFrontendError(error, {
      event: "frontend.render_failed",
      source: "react-boundary",
      route: pathname,
      boundary: "app-route",
      componentArea: "route-tree",
      resetAttempted: true,
      force: true,
      slice: "W-FRONTEND",
      module: "M-APP-ERROR",
      block: "ERROR_BOUNDARY_UI",
    })
    reset()
  }

  return (
    <div
      role="alert"
      data-testid="app-error-boundary"
      data-state="error"
      className="flex min-h-[60vh] flex-col items-center justify-center gap-4 p-6 text-center"
    >
      <h2 className="font-serif text-[22px] font-semibold text-foreground">
        Что-то пошло не так
      </h2>
      <p className="max-w-[32ch] text-[13.5px] leading-relaxed text-muted-foreground">
        Произошла ошибка при отображении этого раздела. Пожалуйста, попробуйте обновить страницу.
      </p>
      <button
        type="button"
        onClick={handleRetry}
        className="inline-flex h-11 items-center justify-center rounded-full bg-primary px-6 text-[13.5px] font-medium text-primary-foreground transition active:scale-[0.98]"
      >
        Попробовать снова
      </button>
    </div>
  )
}
// END_BLOCK: ERROR_BOUNDARY_UI
