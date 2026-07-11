// ############################################################################
// AI_HEADER: MODULE_DEV_THREE_HORIZON_TIMING_FIXTURE — development-only browser fixture loader.
// ROLE: Fetches the isolated three-horizon timing fixture only when a local
//       development preview explicitly opts in through its query parameter.
// ############################################################################

// START_MODULE_CONTRACT: M-DEV-THREE-HORIZON-TIMING-FIXTURE
// purpose: Load a browser-visible V2 timing fixture without calling real day API/auth.
// owns:
//   - lib/dev-fixtures/use-three-horizon-timing-fixture.ts
// inputs: none; this hook is mounted only by the isolated fixture branch.
// outputs: data/loading/error fixture state.
// dependencies: /api/dev-fixtures/three-horizon-timing, packages/contracts.
// side_effects: local development fetch only.
// emitted_logs: none.
// invariants: requests only the guarded local fixture endpoint; production route is unavailable.
// failure_policy: returns an Error for the page error boundary.
// END_MODULE_CONTRACT: M-DEV-THREE-HORIZON-TIMING-FIXTURE

// START_MODULE_MAP: M-DEV-THREE-HORIZON-TIMING-FIXTURE
// public_entrypoints:
//   - useThreeHorizonTimingFixture
// semantic_blocks:
//   - FIXTURE_FETCH: local fixture request lifecycle.
// owned_tests:
//   - e2e/dev-timing-fixture.spec.ts
// END_MODULE_MAP: M-DEV-THREE-HORIZON-TIMING-FIXTURE

"use client"

import { useEffect, useState } from "react"
import type { TodayPayload } from "@/packages/contracts"

// START_BLOCK: FIXTURE_FETCH
export function useThreeHorizonTimingFixture(): {
  data: TodayPayload | null
  loading: boolean
  error: Error | null
} {
  // START_FUNCTION_CONTRACT: F-M-DEV-THREE-HORIZON-TIMING-FIXTURE.useThreeHorizonTimingFixture
  // purpose: Load the three-horizon timing fixture payload from the dev-only local API route.
  // inputs: none.
  // returns: An object containing data, loading, and error states.
  // side_effects: Performs a fetch call to /api/dev-fixtures/three-horizon-timing on mount.
  // emitted_logs: none.
  // error_behavior: returns error object when request fails or endpoint is not reachable.
  // END_FUNCTION_CONTRACT: F-M-DEV-THREE-HORIZON-TIMING-FIXTURE.useThreeHorizonTimingFixture
  const [data, setData] = useState<TodayPayload | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<Error | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    fetch("/api/dev-fixtures/three-horizon-timing")
      .then(async (response) => {
        if (!response.ok) throw new Error("Dev timing fixture is unavailable")
        return response.json() as Promise<TodayPayload>
      })
      .then((payload) => {
        if (!cancelled) setData(payload)
      })
      .catch((reason) => {
        if (!cancelled) setError(reason instanceof Error ? reason : new Error("Dev timing fixture failed"))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  return { data, loading, error }
}
// END_BLOCK: FIXTURE_FETCH
