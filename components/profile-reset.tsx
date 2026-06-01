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
      className="fixed bottom-20 right-4 z-50 flex h-10 w-10 items-center justify-center rounded-full bg-muted/60 text-muted-foreground/60 shadow-sm transition active:scale-95"
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
