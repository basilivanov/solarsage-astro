"use client"

import { useCallback, useMemo } from "react"
import { useRouter } from "next/navigation"

import { ProfileScreen } from "@/components/profile/profile-screen"
import { useAccess } from "@/hooks/use-access"
import { useOnboarded } from "@/hooks/use-onboarded"
import { getProfileMeta } from "@/lib/api/profile-meta"

/**
 * /profile — вкладка профиля.
 *
 * `profileMeta` (хорарные вопросы + рефералка) приходит через API-фасад,
 * как и payload экрана дня. Компонент ProfileScreen про моки уже не знает.
 *
 * Сброс онбординга очищает флаг и возвращает на корневой роут,
 * где показывается OnboardingFlow.
 */
export default function ProfilePage() {
  const router = useRouter()
  const { state, access, setState } = useAccess()
  const { resetOnboarded } = useOnboarded()

  // useMemo, чтобы будущий fetch не дёргался на каждый рендер.
  const profileMeta = useMemo(() => getProfileMeta(), [])

  const onResetOnboarding = useCallback(() => {
    resetOnboarded()
    router.replace("/")
  }, [router, resetOnboarded])

  return (
    <ProfileScreen
      access={access}
      currentState={state}
      onChangeState={setState}
      profileMeta={profileMeta}
      onResetOnboarding={onResetOnboarding}
    />
  )
}
