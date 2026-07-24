// ############################################################################
// AI_HEADER: MODULE_FRONTEND_ERROR_CAPTURE
// ROLE: Client component registering global window error and unhandledrejection handlers.
// DEPENDENCIES: lib/log/capture-error
// GRACE_ANCHORS: [FRONTEND_ERROR_CAPTURE_COMPONENT]
// WAVE: W-FRONTEND-OBSERVABILITY
// ############################################################################

// START_MODULE_CONTRACT: M-FRONTEND-ERROR-CAPTURE
// purpose: Attach window error and unhandledrejection event listeners on mount and log via captureFrontendError.
// owns:
//   - components/telemetry/frontend-error-capture.tsx
// inputs: none
// outputs: null (renders nothing)
// dependencies:
//   - M-LOG-CAPTURE-ERROR (captureFrontendError)
// side_effects:
//   - attaches window listeners on mount, cleans up on unmount
//   - emits logEvent via captureFrontendError
// emitted_logs: frontend.runtime_failed, frontend.promise_rejected
// failure_policy:
//   - errors inside handlers swallowed safely
// END_MODULE_CONTRACT: M-FRONTEND-ERROR-CAPTURE

// START_MODULE_MAP: M-FRONTEND-ERROR-CAPTURE
// public_entrypoints:
//   - FrontendErrorCapture
// semantic_blocks:
//   - COMPONENT: window listener lifecycle
// owned_tests:
//   - __tests__/components/FrontendErrorCapture.test.tsx
// END_MODULE_MAP: M-FRONTEND-ERROR-CAPTURE

"use client"

import { useEffect } from "react"
import { captureFrontendError } from "@/lib/log/capture-error"

// START_BLOCK: COMPONENT
export function FrontendErrorCapture(): null {
  // START_FUNCTION_CONTRACT: F-M-FRONTEND-ERROR-CAPTURE.FrontendErrorCapture
  // purpose: Client component that registers window error and unhandledrejection event handlers.
  // inputs: none
  // returns: null
  // side_effects: attaches window listeners on mount, removes on unmount
  // emitted_logs: frontend.runtime_failed, frontend.promise_rejected
  // END_FUNCTION_CONTRACT: F-M-FRONTEND-ERROR-CAPTURE.FrontendErrorCapture
  useEffect(() => {
    if (typeof window === "undefined") return

    const handleError = (event: ErrorEvent) => {
      const errorInput = event.error || event.message
      captureFrontendError(errorInput, {
        event: "frontend.runtime_failed",
        source: "window.error",
        route: window.location.pathname,
        slice: "W-FRONTEND",
        module: "M-FRONTEND-RUNTIME",
        block: "GLOBAL_ERROR_HANDLER",
      })
    }

    const handleRejection = (event: PromiseRejectionEvent) => {
      captureFrontendError(event.reason, {
        event: "frontend.promise_rejected",
        source: "unhandledrejection",
        route: window.location.pathname,
        slice: "W-FRONTEND",
        module: "M-FRONTEND-RUNTIME",
        block: "GLOBAL_REJECTION_HANDLER",
      })
    }

    window.addEventListener("error", handleError)
    window.addEventListener("unhandledrejection", handleRejection)

    return () => {
      window.removeEventListener("error", handleError)
      window.removeEventListener("unhandledrejection", handleRejection)
    }
  }, [])

  return null
}
// END_BLOCK: COMPONENT
