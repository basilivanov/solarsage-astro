// ############################################################################
// AI_HEADER: MODULE_HOOKS_USE_PROFILE
// ROLE: React hook
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { getProfile, updateProfile } from "@/lib/api/profile"
import {
  apiProfileToProfile,
  loadProfile,
  profileToApiWrite,
  saveProfile,
  type Profile,
} from "@/lib/profile"

export function useProfile() {
  const [profile, setProfile] = useState<Profile>(() => loadProfile())
  const [loaded, setLoaded] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const profileRef = useRef(profile)

  const applyProfile = useCallback((next: Profile) => {
    profileRef.current = next
    setProfile(next)
    saveProfile(next)
  }, [])

  useEffect(() => {
    let active = true
    getProfile()
      .then((value) => {
        if (!active) return
        applyProfile(apiProfileToProfile(value))
        setError(null)
        setLoaded(true)
      })
      .catch((reason: unknown) => {
        if (!active) return
        setError(reason instanceof Error ? reason.message : "Failed to get profile")
      })

    return () => {
      active = false
    }
  }, [applyProfile])

  const update = useCallback(
    async (patch: Partial<Profile>): Promise<Profile> => {
      if (!loaded) {
        const reason = new Error("Profile is still loading")
        setError(reason.message)
        throw reason
      }
      const next = { ...profileRef.current, ...patch }
      setSaving(true)
      setError(null)
      try {
        const saved = apiProfileToProfile(
          await updateProfile(profileToApiWrite(next)),
        )
        applyProfile(saved)
        return saved
      } catch (reason) {
        const message =
          reason instanceof Error ? reason.message : "Failed to update profile"
        setError(message)
        throw reason
      } finally {
        setSaving(false)
      }
    },
    [applyProfile, loaded],
  )

  return { profile, update, loaded, saving, error }
}
