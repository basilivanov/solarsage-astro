
// ############################################################################
// AI_HEADER: GRACE_ERROR_BOUNDARY_VIEW — already-caught error presentation for the day route.
// ROLE: Client error-state view used by the day route; displays an Error and optionally navigates to /debug in explicit dev mode.
// ############################################################################

// START_MODULE_CONTRACT: M-GRACE-COMPONENT-ERROR-BOUNDARY
// purpose: Present a stable role=alert fallback from error/title/message props.
// owns:
//   - components/grace/ErrorBoundary.tsx
// inputs: error; optional title; optional message.
// outputs: error-boundary alert with resolved title/message and optional debug button.
// dependencies: next/navigation useRouter; NEXT_PUBLIC_DEV_MODE.
// side_effects: router.push('/debug') only when the rendered dev button is clicked.
// emitted_logs: none.
// invariants:
//   - This is a presentation component, not a React class error catcher.
//   - data-testid="error-boundary", data-testid="error-message" and role=alert remain stable.
//   - Message priority remains explicit message -> error.message -> generic fallback.
// failure_policy: Displays provided/fallback error text; navigation errors are not caught.
// END_MODULE_CONTRACT: M-GRACE-COMPONENT-ERROR-BOUNDARY

// START_MODULE_MAP: M-GRACE-COMPONENT-ERROR-BOUNDARY
// public_entrypoints:
//   - ErrorBoundary
// semantic_blocks:
//   - ERROR_COPY_RESOLUTION: title, message and dev-mode derivation.
//   - ERROR_ALERT: accessible visual fallback.
//   - DEV_DEBUG_ACTION: conditional /debug navigation.
// owned_tests:
//   - __tests__/components/ErrorBoundary.test.tsx
//   - __tests__/app/day-page.test.tsx (route integration/mocked boundary)
// END_MODULE_MAP: M-GRACE-COMPONENT-ERROR-BOUNDARY

'use client'

import { useRouter } from 'next/navigation'

interface ErrorBoundaryProps {
  error: Error;
  title?: string;
  message?: string;
}

export function ErrorBoundary({ error, title, message }: ErrorBoundaryProps) {
  const router = useRouter()
  const displayTitle = title || 'Ошибка';
  const displayMessage = message || error.message || 'Произошла неизвестная ошибка';
  const isDev = process.env.NEXT_PUBLIC_DEV_MODE === 'true'

  return (
    <div
      className="flex flex-col items-center justify-center px-10 py-12 text-center"
      data-testid="error-boundary"
      role="alert"
    >
      <div className="mb-5 flex h-14 w-14 items-center justify-center rounded-full border border-border/70 bg-card text-muted-foreground">
        <span className="text-2xl">!</span>
      </div>
      <h2 className="font-serif text-[26px] leading-tight tracking-tight text-foreground">
        {displayTitle}
      </h2>
      <p
        className="mt-2 max-w-[26ch] text-[13px] leading-relaxed text-muted-foreground"
        data-testid="error-message"
      >
        {displayMessage}
      </p>
      {isDev && (
        <button
          onClick={() => router.push('/debug')}
          className="mt-6 rounded-full border border-border/70 bg-card px-5 py-2 text-[13px] font-medium text-foreground transition active:scale-[0.98]"
        >
          Debug Info
        </button>
      )}
    </div>
  );
}
