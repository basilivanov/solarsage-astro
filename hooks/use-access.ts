// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_ACCESS
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT: M-HOOKS-USE-ACCESS
// purpose: React hook providing user subscription access status and refresh capability.
// owns:
//   - hooks/use-access.ts
// inputs: none
// outputs: access status state, loaded boolean, error, refresh callback
// dependencies: lib/api/access
// side_effects: credentialed access API fetch
// emitted_logs: none
// failure_policy: sets error state and returns closed access
// END_MODULE_CONTRACT: M-HOOKS-USE-ACCESS

// START_MODULE_MAP: M-HOOKS-USE-ACCESS
// public_entrypoints:
//   - useAccess
// semantic_blocks:
//   - USE_ACCESS_HOOK: User subscription access status hook
// owned_tests:
//   - __tests__/hooks/useAccess.test.ts
// END_MODULE_MAP: M-HOOKS-USE-ACCESS

"use client"

import { useCallback, useEffect, useState } from "react"
import {
  getAccess,
  type AccessInfo,
  type AccessState,
} from "@/lib/api/access"

const CLOSED_ACCESS: AccessInfo = {
  state: "none",
  hasAccess: false,
  accessStart: null,
  accessEnd: null,
  daysLeft: 0,
}

// START_BLOCK: USE_ACCESS_HOOK
export function useAccess(): {
  state: AccessState
  access: AccessInfo
  loaded: boolean
  error: string | null
  refresh: () => Promise<void>
} {
  const [access, setAccess] = useState<AccessInfo>(CLOSED_ACCESS)
  const [loaded, setLoaded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const refresh = useCallback(async () => {
    setLoaded(false)
    setError(null)
    try {
      setAccess(await getAccess())
    } catch (reason) {
      setAccess(CLOSED_ACCESS)
      setError(reason instanceof Error ? reason.message : "Failed to get access")
    } finally {
      setLoaded(true)
    }
  }, [])

  useEffect(() => {
    void refresh()
  }, [refresh])

  return { state: access.state, access, loaded, error, refresh }
}
// END_BLOCK: USE_ACCESS_HOOK
