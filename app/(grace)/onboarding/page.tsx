
// ############################################################################
// AI_HEADER: MODULE_ONBOARDING_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/(grace)/onboarding/page.tsx
// owns:
//   - app/(grace)/onboarding/page.tsx
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
