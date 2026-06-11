
// ############################################################################
// AI_HEADER: MODULE_NATAL-PREVIEW_CTA_BUTTON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// #########################################// START_MODULE_CONTRACT
// purpose: Module: cta-button.tsx
// owns:
//   - components/readings/natal-preview/cta-button.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { Sparkles } from "lucide-react"

type Props = {
  priceKopecks: number
  onClick?: () => void
}

export function CtaButton({ priceKopecks, onClick }: Props) {
  const price = Math.round(priceKopecks / 100)

  return (
    <div className="space-y-3">
      <button
        type="button"
        onClick={onClick}
        className="group relative w-full overflow-hidden rounded-2xl bg-primary px-4 py-4 text-center transition active:scale-[0.99]"
      >
        <div className="absolute inset-0 bg-gradient-to-r from-primary to-primary/90" />
        <div className="relative flex items-center justify-center gap-2">
          <Sparkles className="h-4 w-4 text-primary-foreground/80" />
          <span className="text-[16px] font-semibold text-primary-foreground">
            Полный отчёт за {price} ₽
          </span>
        </div>
      </button>
      <p className="text-center text-[11px] text-muted-foreground/60">
        Разбор по точным данным рождения · 13 разделов
      </p>
    </div>
  )
}
