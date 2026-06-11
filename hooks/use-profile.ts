
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_PROFILE
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: React hook — hooks/use-profile.ts
// owns:
//   - hooks/use-profile.ts
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
import {
  DEFAULT_PROFILE,
  loadProfile,
  saveProfile,
  type Profile,
} from "@/lib/profile"

export function useProfile() {
  const [profile, setProfile] = useState<Profile>(DEFAULT_PROFILE)
  const [loaded, setLoaded] = useState(false)

  useEffect(() => {
    setProfile(loadProfile())
    setLoaded(true)
  }, [])

  const update = useCallback((patch: Partial<Profile>) => {
    setProfile((prev) => {
      const next = { ...prev, ...patch }
      saveProfile(next)
      return next
    })
  }, [])

  return { profile, update, loaded }
}
