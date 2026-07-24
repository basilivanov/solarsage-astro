// ############################################################################
// AI_HEADER: MODULE_APP_ONBOARDING_PAGE
// ROLE: Onboarding completion page adapter with promo prefill and exact-time support.
// DEPENDENCIES: react, next/navigation, components/onboarding/onboarding-flow, lib/api/profile, lib/reducers/onboarding-reducer
// GRACE_ANCHORS: [APP_ONBOARDING_PAGE]
// WAVE: W-NAMED-PROMO-CAMPAIGN
// ############################################################################

// START_MODULE_CONTRACT: M-APP-ONBOARDING-PAGE
// purpose: Render onboarding and transition completed profile into current day experience, with profile prefill and exact-time requirements for promo modes.
// owns:
//   - app/(grace)/onboarding/page.tsx
// inputs: requiredFor searchParam query ("promoNatal" | "promoBase")
// outputs: OnboardingPage React component
// dependencies:
//   - M-ONBOARDING-FLOW (OnboardingFlow)
//   - M-API-PROFILE (getProfile)
//   - M-REDUCERS-ONBOARDING-REDUCER (onboardingStateFromProfile)
// side_effects: fetches profile, sets onboarded hook state, navigates to /day/<TODAY>
// emitted_logs: none
// invariants:
//   - promo search params read requiredFor strictly without reading or expecting token
//   - profile loading exposes role="status" and aria-busy="true"
//   - profile load errors expose role="alert" with retry button and do not complete onboarding
//   - ordinary /onboarding path is preserved without query requirements
// failure_policy: profile load failures render safe alert and allow retry
// END_MODULE_CONTRACT: M-APP-ONBOARDING-PAGE

// START_MODULE_MAP: M-APP-ONBOARDING-PAGE
// public_entrypoints:
//   - OnboardingPage (default)
// semantic_blocks:
//   - ONBOARDING_PAGE_CONTENT: OnboardingContent component
// owned_tests:
//   - __tests__/components/OnboardingFlow.test.tsx
// END_MODULE_MAP: M-APP-ONBOARDING-PAGE

"use client"

import { Suspense, useCallback, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { OnboardingFlow } from "@/components/onboarding/onboarding-flow"
import { useOnboarded } from "@/hooks/use-onboarded"
import { TODAY } from "@/lib/today"
import { toDateParam } from "@/lib/date"
import { getProfile } from "@/lib/api/profile"
import { apiProfileToProfile, type Profile } from "@/lib/profile"
import { onboardingStateFromProfile, type OnboardingState } from "@/lib/reducers/onboarding-reducer"

function OnboardingContent() {
  const router = useRouter()
  const searchParams = useSearchParams()
  const { setOnboarded } = useOnboarded()

  const rawRequiredFor = searchParams?.get("requiredFor")
  const requiredFor =
    rawRequiredFor === "promoNatal" || rawRequiredFor === "promoBase"
      ? rawRequiredFor
      : null

  const [profileState, setProfileState] = useState<{
    profile: Profile | null
    loading: boolean
    error: string | null
  }>({
    profile: null,
    loading: Boolean(requiredFor),
    error: null,
  })

  const loadProfileData = useCallback(async () => {
    if (!requiredFor) return
    setProfileState((prev) => ({ ...prev, loading: true, error: null }))
    try {
      const read = await getProfile()
      const prof = apiProfileToProfile(read)
      setProfileState({ profile: prof, loading: false, error: null })
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Не удалось загрузить профиль"
      setProfileState({ profile: null, loading: false, error: msg })
    }
  }, [requiredFor])

  useEffect(() => {
    if (requiredFor) {
      loadProfileData()
    }
  }, [loadProfileData, requiredFor])

  const completeOnboarding = useCallback(() => {
    setOnboarded(true)
    router.replace(`/day/${toDateParam(TODAY)}`)
  }, [router, setOnboarded])

  if (requiredFor) {
    if (profileState.loading) {
      return (
        <div
          role="status"
          aria-busy="true"
          className="flex min-h-screen items-center justify-center bg-background"
        >
          <div className="flex flex-col items-center gap-3">
            <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
            <span className="text-sm text-muted-foreground">Загрузка профиля...</span>
          </div>
        </div>
      )
    }

    if (profileState.error) {
      return (
        <div
          role="alert"
          className="flex min-h-screen items-center justify-center bg-background px-6"
        >
          <div className="flex flex-col items-center gap-3 text-center">
            <p className="text-sm text-destructive">{profileState.error}</p>
            <button
              type="button"
              onClick={loadProfileData}
              className="rounded-lg bg-primary px-4 py-2 text-sm font-semibold text-primary-foreground hover:bg-primary/90"
            >
              Повторить
            </button>
          </div>
        </div>
      )
    }

    const initialState: OnboardingState | undefined = profileState.profile
      ? onboardingStateFromProfile(profileState.profile)
      : undefined

    return (
      <OnboardingFlow
        onComplete={completeOnboarding}
        initialState={initialState}
        requireExactBirthTime={requiredFor === "promoNatal"}
      />
    )
  }

  return <OnboardingFlow onComplete={completeOnboarding} />
}

export default function OnboardingPage() {
  return (
    <Suspense
      fallback={
        <div role="status" aria-busy="true" className="flex min-h-screen items-center justify-center bg-background">
          <div className="h-8 w-8 animate-spin rounded-full border-4 border-primary border-t-transparent" />
        </div>
      }
    >
      <OnboardingContent />
    </Suspense>
  )
}
