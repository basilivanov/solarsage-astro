
// ############################################################################
// AI_HEADER: MODULE_MONETIZATION_TRIAL_BANNER
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/monetization/trial-banner.tsx
// owns:
//   - components/monetization/trial-banner.tsx
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

'use client'

import { Sparkles } from "lucide-react"
import { useRouter } from 'next/navigation'

export function TrialBanner({ daysLeft }: { daysLeft: number }) {
  const router = useRouter()
  const isDev = process.env.NEXT_PUBLIC_DEV_MODE === 'true'

  return (
    <div className="mx-5 flex items-center gap-3 rounded-xl border border-border/70 bg-secondary/40 px-4 py-3">
      <div className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-accent text-accent-foreground">
        <Sparkles className="h-4 w-4" strokeWidth={1.75} />
      </div>
      <div className="min-w-0 flex-1">
        <div className="text-[12px] font-medium text-foreground">
          14 дней бесплатного доступа
        </div>
        <div className="text-[11.5px] text-muted-foreground">
          Осталось {daysLeft}{" "}
          {daysLeft === 1 ? "день" : daysLeft < 5 ? "дня" : "дней"}
        </div>
        {isDev && (
          <button
            onClick={() => router.push('/debug')}
            className="text-xs text-purple-600 underline mt-1"
          >
            🔍 Debug
          </button>
        )}
      </div>
      <button
        type="button"
        className="rounded-full border border-border/70 bg-card px-3 py-1.5 text-[11px] font-medium text-foreground transition active:scale-[0.97]"
      >
        Подписка
      </button>
    </div>
  )
}
