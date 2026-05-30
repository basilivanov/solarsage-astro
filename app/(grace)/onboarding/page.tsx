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
