
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_ACCESS
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: React hook — hooks/use-access.ts
// owns:
//   - hooks/use-access.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

"use client"

import { useCallback, useEffect, useState } from "react"
import type { AccessInfo, AccessState } from "@/lib/api/access"
import { getAccess } from "@/lib/api/access"
import { STORAGE_KEYS } from "@/lib/storage-keys"

const VALID: AccessState[] = ["trial", "subscription", "expired", "none"]

function readState(): AccessState {
  if (typeof window === "undefined") return "trial"
  try {
    const saved = window.localStorage.getItem(
      STORAGE_KEYS.accessState,
    ) as AccessState | null
    if (saved && VALID.includes(saved)) return saved
  } catch {}
  return "trial"
}

export function useAccess(): {
  state: AccessState
  access: AccessInfo
  setState: (s: AccessState) => void
} {
  const [state, setStateInternal] = useState<AccessState>("trial")

  useEffect(() => {
    setStateInternal(readState())
  }, [])

  const setState = useCallback((s: AccessState) => {
    setStateInternal(s)
    try {
      window.localStorage.setItem(STORAGE_KEYS.accessState, s)
    } catch {}
  }, [])

  return { state, access: getAccess(state), setState }
}
