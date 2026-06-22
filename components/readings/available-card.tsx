
// ############################################################################
// AI_HEADER: MODULE_READINGS_AVAILABLE_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################
// START_MODULE_CONTRACT
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
      className="card-glow-hover group relative flex w-full flex-col items-start gap-4 overflow-hidden rounded-2xl border border-border/70 bg-card p-5 text-left transition active:scale-[0.99] hover:-translate-y-0.5"
    >
      {/* Decorative corner glow */}
      <div
        aria-hidden
        className="pointer-events-none absolute -right-8 -top-8 h-24 w-24 rounded-full opacity-0 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background: "radial-gradient(circle, oklch(0.55 0.08 305 / 0.12), transparent 70%)",
        }}
      />
      <div className="relative flex h-11 w-11 items-center justify-center rounded-full bg-primary/10 text-primary transition-transform duration-300 group-hover:scale-110">
        <Icon className="h-[22px] w-[22px]" strokeWidth={1.6} />
      </div>

      <div className="relative flex w-full flex-col gap-1.5">
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

      <div className="relative mt-1 flex items-center gap-1.5 text-[13px] font-medium text-primary">
        <span>Открыть</span>
        <ArrowRight
          className="h-4 w-4 transition-transform group-hover:translate-x-1 group-active:translate-x-0.5"
          strokeWidth={1.75}
        />
      </div>
    </button>
  )
}
