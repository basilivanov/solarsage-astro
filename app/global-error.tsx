// ############################################################################
// AI_HEADER: MODULE_APP_GLOBAL_ERROR
// ROLE: Root/global error boundary for React/Next errors according to Next 16 specs.
// DEPENDENCIES: lib/log/capture-error
// GRACE_ANCHORS: [APP_GLOBAL_ERROR_BOUNDARY]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-APP-GLOBAL-ERROR
// purpose: Next.js root global-error boundary component that logs render errors and presents root HTML/body fallback.
// owns:
//   - app/global-error.tsx
// inputs: error (Error & { digest?: string }), reset (() => void)
// outputs: TSX html/body fallback with role="alert", data-testid="global-error-boundary", data-state="error"
// dependencies:
//   - M-LOG-CAPTURE-ERROR (captureFrontendError)
// side_effects:
//   - logs frontend.render_failed event on mount/error change
//   - logs frontend.render_failed event with reset_attempted=true on retry click
// emitted_logs: frontend.render_failed
// failure_policy:
//   - internal errors swallowed safely; fallback UI remains rendered
// END_MODULE_CONTRACT: M-APP-GLOBAL-ERROR

// START_MODULE_MAP: M-APP-GLOBAL-ERROR
// public_entrypoints:
//   - GlobalError (default)
// semantic_blocks:
//   - GLOBAL_ERROR_BOUNDARY_UI: root HTML document fallback UI
// owned_tests:
//   - __tests__/app/error-boundaries.test.tsx
// END_MODULE_MAP: M-APP-GLOBAL-ERROR

"use client"

import { useEffect } from "react"
import { captureFrontendError } from "@/lib/log/capture-error"

// START_BLOCK: GLOBAL_ERROR_BOUNDARY_UI
export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string }
  reset: () => void
}) {
  // START_FUNCTION_CONTRACT: F-M-APP-GLOBAL-ERROR.GlobalError
  // purpose: Next.js root global-error boundary component rendering <html><body> document fallback UI.
  // inputs: error — Error instance, reset — callback function to attempt recovering
  // returns: JSX.Element
  // side_effects: logs frontend.render_failed via captureFrontendError
  // emitted_logs: frontend.render_failed
  // END_FUNCTION_CONTRACT: F-M-APP-GLOBAL-ERROR.GlobalError
  const pathname = typeof window !== "undefined" ? window.location.pathname : ""

  useEffect(() => {
    captureFrontendError(error, {
      event: "frontend.render_failed",
      source: "react-boundary",
      route: pathname,
      boundary: "global-root",
      componentArea: "root-layout",
      resetAttempted: false,
      slice: "W-FRONTEND",
      module: "M-APP-GLOBAL-ERROR",
      block: "GLOBAL_ERROR_BOUNDARY_UI",
    })
  }, [error, pathname])

  const handleRetry = () => {
    captureFrontendError(error, {
      event: "frontend.render_failed",
      source: "react-boundary",
      route: pathname,
      boundary: "global-root",
      componentArea: "root-layout",
      resetAttempted: true,
      force: true,
      slice: "W-FRONTEND",
      module: "M-APP-GLOBAL-ERROR",
      block: "GLOBAL_ERROR_BOUNDARY_UI",
    })
    reset()
  }

  return (
    <html lang="ru" className="bg-background">
      <body className="font-sans antialiased">
        <div
          role="alert"
          data-testid="global-error-boundary"
          data-state="error"
          className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center"
        >
          <h2 className="font-serif text-[24px] font-semibold text-foreground">
            Произошла критическая ошибка
          </h2>
          <p className="max-w-[34ch] text-[14px] leading-relaxed text-muted-foreground">
            Не удалось загрузить приложение. Нажмите кнопку ниже, чтобы попробовать перезапустить.
          </p>
          <button
            type="button"
            onClick={handleRetry}
            className="inline-flex h-12 items-center justify-center rounded-full bg-primary px-7 text-[14px] font-medium text-primary-foreground transition active:scale-[0.98]"
          >
            Попробовать снова
          </button>
        </div>
      </body>
    </html>
  )
}
// END_BLOCK: GLOBAL_ERROR_BOUNDARY_UI
