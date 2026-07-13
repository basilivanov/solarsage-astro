
// ############################################################################
// AI_HEADER: APP_ONBOARDING_PAGE — onboarding completion and day-route adapter.
// ROLE: Client Next.js page called by /onboarding; hosts OnboardingFlow and synchronizes successful completion with onboarded state and the current day route.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-ONBOARDING-PAGE
// purpose: Render onboarding and transition a completed profile into the canonical current-day experience.
// owns:
//   - app/(grace)/onboarding/page.tsx
// inputs: OnboardingFlow completion callback, useOnboarded setter and TODAY.
// outputs: OnboardingFlow with a stable completion handler.
// dependencies: React useCallback; next/navigation; OnboardingFlow; useOnboarded; TODAY; toDateParam.
// side_effects: Persists onboarded state through the hook and performs router.replace navigation.
// emitted_logs: none (logging is delegated to OnboardingFlow/useOnboarded).
// invariants:
//   - Successful completion marks onboarded before replacing the route.
//   - Destination is /day/<toDateParam(TODAY)>.
// failure_policy: Save failures remain in OnboardingFlow; navigation/render errors are delegated to Next/route boundary.
// END_MODULE_CONTRACT: M-APP-ONBOARDING-PAGE

// START_MODULE_MAP: M-APP-ONBOARDING-PAGE
// public_entrypoints:
//   - OnboardingPage (default).
// semantic_blocks:
//   - COMPLETION_TRANSITION: synchronize onboarded state and canonical redirect.
//   - PAGE_COMPOSITION: render OnboardingFlow.
// owned_tests:
//   - __tests__/components/OnboardingFlow.test.tsx (indirect flow coverage).
// END_MODULE_MAP: M-APP-ONBOARDING-PAGE

'use client'

import { useCallback } from 'react'
import { useRouter } from 'next/navigation'
import { OnboardingFlow } from '@/components/onboarding/onboarding-flow'
import { useOnboarded } from '@/hooks/use-onboarded'
import { TODAY } from '@/lib/today'
import { toDateParam } from '@/lib/date'

export default function OnboardingPage() {
  const router = useRouter()
  const { setOnboarded } = useOnboarded()

  const completeOnboarding = useCallback(() => {
    setOnboarded(true)
    router.replace(`/day/${toDateParam(TODAY)}`)
  }, [router, setOnboarded])

  return <OnboardingFlow onComplete={completeOnboarding} />
}
