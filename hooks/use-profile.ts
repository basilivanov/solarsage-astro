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
