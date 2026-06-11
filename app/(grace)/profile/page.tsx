
// ############################################################################
// AI_HEADER: MODULE_PROFILE_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/profile/page.tsx
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
import { useRouter } from "next/navigation"

import { ProfileScreen } from "@/components/profile/profile-screen"
import { useAccess } from "@/hooks/use-access"
import { useOnboarded } from "@/hooks/use-onboarded"
import { getProfileMeta } from "@/lib/api/profile-meta"
import type { ProfileMeta } from "@/lib/profile-meta"

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

  const [profileMeta, setProfileMeta] = useState<ProfileMeta>({
    horary: {
      weeklyFreeAvailable: false,
      weeklyFreeExpiresAt: null,
      nextWeeklyFreeAt: null,
      bonusCredits: 0,
      paidCredits: 0,
      canPurchase: true,
    },
    referral: { count: 0, bonusDays: 0, rewardDays: 7, inviteUrl: "" },
  })

  useEffect(() => {
    getProfileMeta().then(setProfileMeta).catch(() => {})
  }, [])

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
