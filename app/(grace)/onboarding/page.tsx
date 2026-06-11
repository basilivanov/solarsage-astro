
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/onboarding/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: React state management
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
// AI_HEADER
// module: M-WEB-ONBOARDING-PAGE
// wave: W-2.7
// purpose: Onboarding flow (migrated from legacy)

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
