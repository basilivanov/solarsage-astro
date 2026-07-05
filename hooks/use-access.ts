// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_ACCESS
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
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

export function useAccess(): {
  state: AccessState
  access: AccessInfo
  loaded: boolean
  error: string | null
  refresh: () => Promise<void>
  setState: (_state: AccessState) => void
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

  const setState = useCallback((_state: AccessState) => {
    // Real access is backend-owned. The old localStorage-backed setter is kept
    // as a compatibility no-op for dev-only controls.
  }, [])

  return { state: access.state, access, loaded, error, refresh, setState }
}
