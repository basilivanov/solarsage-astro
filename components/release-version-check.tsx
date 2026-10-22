// ############################################################################
// AI_HEADER: MODULE_RELEASE_VERSION_CHECK
// ROLE: Client release freshness guard comparing the baked frontend SHA with /api/health.
// DEPENDENCIES: React, GET /api/health
// GRACE_ANCHORS: [RELEASE_VERSION_CHECK, UPDATE_BANNER]
// WAVE: W-CACHE-DELIVERY-HARDENING
// ############################################################################

// START_MODULE_CONTRACT: M-RELEASE-VERSION-CHECK
// purpose: Detect a frontend bundle older than the running API release and offer
//   an explicit reload without interrupting the user's current screen.
// owns:
//   - components/release-version-check.tsx
// inputs:
//   - process.env.NEXT_PUBLIC_RELEASE_SHA (build-time public release sha)
//   - GET /api/health release_sha
//   - document visibilitychange events
// outputs:
//   - null while versions match or either sha is unknown
//   - fixed bottom banner with a manual "Обновить" button on mismatch
// dependencies:
//   - React (useEffect, useState)
//   - Fetch API
// side_effects:
//   - fetches /api/health on mount and when the document becomes visible
//   - reloads the page only after the user clicks the banner button
// emitted_logs: none
// invariants:
//   - no fetch when NEXT_PUBLIC_RELEASE_SHA is empty or unknown
//   - no banner when server release_sha is missing or unknown
//   - fetch/parse failures are silent and never hide existing app content
//   - no automatic reload is performed
// failure_policy: fail open — version-check errors never break the application.
// END_MODULE_CONTRACT: M-RELEASE-VERSION-CHECK

// START_MODULE_MAP: M-RELEASE-VERSION-CHECK
// public_entrypoints:
//   - ReleaseVersionCheck
// semantic_blocks:
//   - VERSION_PROBE: build/server sha comparison on mount and resume.
//   - UPDATE_BANNER: fixed, non-blocking manual reload affordance.
// owned_tests:
//   - __tests__/components/release-version-check.test.tsx
// END_MODULE_MAP: M-RELEASE-VERSION-CHECK

"use client"

import { useEffect, useState, type ReactElement } from "react"

const HEALTH_ENDPOINT = "/api/health"

// START_BLOCK: VERSION_PROBE
function normalizeReleaseSha(value: unknown): string {
  if (typeof value !== "string") return ""
  const trimmed = value.trim()
  if (!trimmed || trimmed === "unknown") return ""
  return trimmed
}
// END_BLOCK: VERSION_PROBE

// START_BLOCK: UPDATE_BANNER
// START_FUNCTION_CONTRACT: F-M-RELEASE-VERSION-CHECK.ReleaseVersionCheck
// purpose: Compare the bundle release sha with the API release and render a
//   manual update banner on mismatch.
// inputs: none.
// returns: null or the fixed release-update banner.
// side_effects: fetches /api/health on mount/visibility; reloads on click.
// emitted_logs: none.
// error_behavior: swallows fetch and parse errors.
// END_FUNCTION_CONTRACT: F-M-RELEASE-VERSION-CHECK.ReleaseVersionCheck
export function ReleaseVersionCheck(): ReactElement | null {
  const [isMismatch, setIsMismatch] = useState(false)

  useEffect(() => {
    const buildSha = normalizeReleaseSha(process.env.NEXT_PUBLIC_RELEASE_SHA)
    if (!buildSha) return

    let cancelled = false
    let inFlight = false

    const checkRelease = async () => {
      if (inFlight) return
      inFlight = true
      try {
        const response = await fetch(HEALTH_ENDPOINT, { cache: "no-store" })
        if (!response.ok) return

        const payload: unknown = await response.json()
        if (!payload || typeof payload !== "object") return

        const serverSha = normalizeReleaseSha(
          (payload as { release_sha?: unknown }).release_sha,
        )
        if (!serverSha) {
          if (!cancelled) setIsMismatch(false)
          return
        }
        if (!cancelled) setIsMismatch(serverSha !== buildSha)
      } catch {
        // Cache freshness checking is best-effort and must never affect UX.
      } finally {
        inFlight = false
      }
    }

    void checkRelease()

    const handleVisibilityChange = () => {
      if (document.visibilityState === "visible") {
        void checkRelease()
      }
    }

    document.addEventListener("visibilitychange", handleVisibilityChange)

    return () => {
      cancelled = true
      document.removeEventListener("visibilitychange", handleVisibilityChange)
    }
  }, [])

  if (!isMismatch) return null

  return (
    <div
      data-testid="release-update-banner"
      role="status"
      aria-live="polite"
      className="pointer-events-none fixed inset-x-4 bottom-4 z-50 mx-auto flex max-w-md items-center justify-between gap-3 rounded-2xl border border-border bg-card/95 p-3 text-sm shadow-lg backdrop-blur supports-[backdrop-filter]:bg-card/80"
    >
      <span className="text-foreground">Доступна новая версия</span>
      <button
        type="button"
        data-testid="release-update-reload"
        onClick={() => window.location.reload()}
        className="pointer-events-auto inline-flex h-9 shrink-0 items-center justify-center rounded-full bg-primary px-4 text-sm font-medium text-primary-foreground transition active:scale-[0.99]"
      >
        Обновить
      </button>
    </div>
  )
}
// END_BLOCK: UPDATE_BANNER
