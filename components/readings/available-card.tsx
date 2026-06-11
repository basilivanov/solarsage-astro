
// ############################################################################
// AI_HEADER: MODULE_READINGS_AVAILABLE_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// #########################################// START_MODULE_CONTRACT
// purpose: Module: available-card.tsx
// owns:
//   - components/readings/available-card.tsx
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

import { ArrowRight, type LucideIcon } from "lucide-react"

type Props = {
  icon: LucideIcon
  title: string
  description: string
  teaser?: string
  onClick: () => void
}

export function AvailableCard({ icon: Icon, title, description, teaser, onClick }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="group flex w-full flex-col items-start gap-4 rounded-2xl border border-border/70 bg-card p-5 text-left transition active:scale-[0.99]"
    >
      <div className="flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary">
        <Icon className="h-[22px] w-[22px]" strokeWidth={1.6} />
      </div>

      <div className="flex w-full flex-col gap-1.5">
        <h3 className="font-serif text-[20px] leading-tight tracking-tight text-foreground">
          {title}
        </h3>
        <p className="text-pretty text-[13.5px] leading-relaxed text-muted-foreground">
          {description}
        </p>
        {teaser ? (
          <p className="mt-1 text-[12px] leading-snug text-foreground/50">{teaser}</p>
        ) : null}
      </div>

      <div className="mt-1 flex items-center gap-1.5 text-[13px] font-medium text-primary">
        <span>Открыть</span>
        <ArrowRight
          className="h-4 w-4 transition-transform group-active:translate-x-0.5"
          strokeWidth={1.75}
        />
      </div>
    </button>
  )
}
