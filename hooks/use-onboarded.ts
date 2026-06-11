
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_ONBOARDED
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: React hook — hooks/use-onboarded.ts
// owns:
//   - hooks/use-onboarded.ts
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

import { STORAGE_KEYS } from "@/lib/storage-keys"
import { logger } from "@/lib/log"

export function useOnboarded() {
  const [onboarded, setOnboardedState] = useState<boolean | null>(null)

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEYS.onboarded)
      const val = saved === "1"
      logger.debug('[Onboarded] Read from localStorage', { extra: { saved, val } })
      if (val) {
        setOnboardedState(true)
        return
      }
    } catch (e) {
      logger.warn('[Onboarded] localStorage error', { extra: { error: String(e) } })
    }

    // localStorage empty — check backend profile
    fetch('/api/profile', { credentials: 'include' })
      .then(r => r.ok ? r.json() : null)
      .then(profile => {
        if (profile?.isOnboarded) {
          logger.info('[Onboarded] Backend says onboarded — syncing localStorage')
          try { window.localStorage.setItem(STORAGE_KEYS.onboarded, "1") } catch {}
          setOnboardedState(true)
        } else {
          setOnboardedState(false)
        }
      })
      .catch(() => setOnboardedState(false))
  }, [])

  const setOnboarded = useCallback((value: boolean) => {
    try {
      logger.info('[Onboarded] Setting', { extra: { value } })
      if (value) {
        window.localStorage.setItem(STORAGE_KEYS.onboarded, "1")
      } else {
        window.localStorage.removeItem(STORAGE_KEYS.onboarded)
      }
    } catch {}
    setOnboardedState(value)
  }, [])

  const resetOnboarded = useCallback(() => {
    logger.info('[Onboarded] Reset')
    try {
      window.localStorage.removeItem(STORAGE_KEYS.onboarded)
    } catch {}
    setOnboardedState(false)
  }, [])

  logger.debug('[Onboarded] Returning', { extra: { onboarded } })
  return { onboarded, setOnboarded, resetOnboarded }
}
