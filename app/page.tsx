// AI_HEADER
// module: M-WEB-HOME-REDIRECT
// wave: W-2.7
// purpose: Check onboarding status and redirect accordingly

'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useOnboarded } from '@/hooks/use-onboarded'

export default function HomePage() {
  const router = useRouter()
  const { onboarded, loading } = useOnboarded()

  useEffect(() => {
    if (loading) return

    if (onboarded) {
      router.push('/day/today')
    } else {
      router.push('/onboarding')
    }
  }, [onboarded, loading, router])

  return (
    <div className="flex items-center justify-center min-h-screen">
      <div className="text-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto mb-4"></div>
        <p className="text-gray-600">Загрузка...</p>
      </div>
    </div>
  )
}
