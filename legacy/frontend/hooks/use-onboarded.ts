"use client"

import { useCallback, useEffect, useState } from "react"

import { STORAGE_KEYS } from "@/lib/storage-keys"

/**
 * Единственный источник истины для флага онбординга.
 *
 * Раньше эта же логика жила в `app/page.tsx` (чтение + запись),
 * `components/app-shell.tsx` (чтение) и `app/(app)/profile/page.tsx`
 * (удаление). Каждый раз дублировался один и тот же паттерн:
 * `useState<boolean | null>(null)` + `useEffect` с try/catch + анти-мигание.
 *
 * Теперь все три кейса закрыты этим хуком:
 *   - `onboarded` — `null` пока не прочитали из storage (SSR / первый рендер),
 *     потом `true` или `false`. Использовать `=== true` / `=== false`,
 *     чтобы не показывать UI на этапе `null` (анти-мигание).
 *   - `setOnboarded(true)` — отметить онбординг пройденным.
 *   - `resetOnboarded()` — стереть флаг (для dev-сброса в профиле).
 */
export function useOnboarded() {
  const [onboarded, setOnboardedState] = useState<boolean | null>(null)

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem(STORAGE_KEYS.onboarded)
      setOnboardedState(saved === "1")
    } catch {
      setOnboardedState(false)
    }
  }, [])

  const setOnboarded = useCallback((value: boolean) => {
    try {
      if (value) {
        window.localStorage.setItem(STORAGE_KEYS.onboarded, "1")
      } else {
        window.localStorage.removeItem(STORAGE_KEYS.onboarded)
      }
    } catch {}
    setOnboardedState(value)
  }, [])

  const resetOnboarded = useCallback(() => {
    try {
      window.localStorage.removeItem(STORAGE_KEYS.onboarded)
    } catch {}
    setOnboardedState(false)
  }, [])

  return { onboarded, setOnboarded, resetOnboarded }
}
