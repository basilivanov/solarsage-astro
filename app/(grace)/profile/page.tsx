
// ############################################################################
// AI_HEADER: APP_PROFILE_PAGE — profile screen data-composition route.
// ROLE: Client Next.js page called by /profile; combines access hook state with asynchronously loaded profile meta for ProfileScreen.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-PROFILE-PAGE
// purpose: Render ProfileScreen with current access and horary/referral metadata from the real API facade.
// owns:
//   - app/(grace)/profile/page.tsx
// inputs: useAccess state and getProfileMeta response.
// outputs: ProfileScreen with access, currentState and profileMeta.
// dependencies: React useEffect/useState; ProfileScreen; useAccess; getProfileMeta; ProfileMeta.
// side_effects: Performs one profile-meta request and updates React state.
// emitted_logs: none.
// invariants:
//   - A complete zero/default ProfileMeta is available before the request resolves.
//   - Fetch failure preserves the safe default instead of injecting mock data.
// failure_policy: Profile-meta rejection is intentionally absorbed with the default; render errors bubble to the route boundary.
// END_MODULE_CONTRACT: M-APP-PROFILE-PAGE

// START_MODULE_MAP: M-APP-PROFILE-PAGE
// public_entrypoints:
//   - ProfilePage (default).
// semantic_blocks:
//   - DEFAULT_META: initialize honest empty horary/referral values.
//   - META_LOAD: replace defaults only after a successful real API response.
//   - PAGE_COMPOSITION: render ProfileScreen.
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx (indirect screen contract).
// END_MODULE_MAP: M-APP-PROFILE-PAGE
"use client"

import { useEffect, useState } from "react"

import { ProfileScreen } from "@/components/profile/profile-screen"
import { useAccess } from "@/hooks/use-access"
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
  const { state, access } = useAccess()

  const [profileMeta, setProfileMeta] = useState<ProfileMeta>({
    horary: {
      weeklyFreeAvailable: false,
      weeklyFreeExpiresAt: null,
      nextWeeklyFreeAt: null,
      bonusCredits: 0,
      paidCredits: 0,
      canPurchase: false,
    },
    referral: { count: 0, bonusDays: 0, rewardDays: 14, inviteUrl: "" },
  })

  useEffect(() => {
    getProfileMeta().then(setProfileMeta).catch(() => {})
  }, [])

  return (
    <ProfileScreen
      access={access}
      currentState={state}
      profileMeta={profileMeta}
    />
  )
}
