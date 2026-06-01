'use client'

import { useRouter } from 'next/navigation'
import { useState } from 'react'

export function DebugButton() {
  const router = useRouter()
  const [isVisible, setIsVisible] = useState(true)

  // Only show in dev mode
  const isDev = process.env.NEXT_PUBLIC_DEV_MODE === 'true'

  if (!isDev || !isVisible) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2">
      {/* Debug button */}
      <button
        onClick={() => router.push('/debug')}
        className="bg-purple-600 hover:bg-purple-700 text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg transition-all"
        title="Open Debug Page"
      >
        <span className="text-2xl">🔍</span>
      </button>

      {/* Hide button */}
      <button
        onClick={() => setIsVisible(false)}
        className="bg-gray-600 hover:bg-gray-700 text-white rounded-full w-14 h-14 flex items-center justify-center shadow-lg transition-all text-xs"
        title="Hide Debug Button"
      >
        ✕
      </button>
    </div>
  )
}
