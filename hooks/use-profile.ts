
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_PROFILE
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI use-profile — component
// owns:
//   - hooks/use-profile.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
