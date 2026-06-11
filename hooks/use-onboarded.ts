
// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_ONBOARDED
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: API client for use-onboarded
// owns:
//   - hooks/use-onboarded.ts
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: Network calls to API; Logging via v2 logging spine; React state management
// emitted_logs: v2 logging: logEvent/logStart/logSuccess/logFailure (frontend) or logger.* (backend)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
