
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_PROFILE_RESET
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/profile-reset.tsx
// owns:
//   - components/profile-reset.tsx
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

import { useState } from "react"
import { useRouter } from "next/navigation"

const ADMIN_TG_IDS = [833478509] // basil_ivanov

function isAdmin(): boolean {
  try {
    const tg = window?.Telegram?.WebApp
    const userId = tg?.initDataUnsafe?.user?.id
    return typeof userId === 'number' && ADMIN_TG_IDS.includes(userId)
  } catch {
    return false
  }
}

export function ProfileReset() {
  const router = useRouter()
  const [resetting, setResetting] = useState(false)

  if (!isAdmin()) return null

  async function handleReset() {
    if (resetting) return
    if (!confirm('Сбросить профиль? Все данные будут удалены.')) return
    setResetting(true)
    try {
      // Clear backend profile
      await fetch('/api/profile', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify({ birth: { birthday: null, birthTime: null, birthCity: null, birthLat: null, birthLon: null, birthTz: null } }),
      })
      // Clear browser
      localStorage.clear()
      sessionStorage.clear()
      document.cookie.split(';').forEach((c) => {
        document.cookie = c.replace(/^ +/, '').replace(/=.*/, '=;expires=' + new Date().toUTCString() + ';path=/')
      })
      router.push('/')
    } catch {
      setResetting(false)
    }
  }

  return (
    <button
      onClick={handleReset}
      className="fixed top-4 right-4 z-50 flex h-8 w-8 items-center justify-center rounded-full bg-muted/40 text-muted-foreground/40 shadow-sm transition active:scale-95 opacity-30"
      title="Сбросить профиль и начать заново"
    >
      {resetting ? (
        <div className="h-4 w-4 animate-spin rounded-full border-2 border-muted-foreground border-t-transparent" />
      ) : (
        <span className="text-lg">↺</span>
      )}
    </button>
  )
}
