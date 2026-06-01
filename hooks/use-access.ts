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
