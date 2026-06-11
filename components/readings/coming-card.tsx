
// ############################################################################
// AI_HEADER: MODULE_READINGS_COMING_CARD
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-HORARY-READINGS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/readings/coming-card.tsx
// owns:
//   - components/readings/coming-card.tsx
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

"use client"

import type { LucideIcon } from "lucide-react"

type Props = {
  icon: LucideIcon
  title: string
  description: string
  onClick: () => void
  isLast?: boolean
}

export function ComingCard({ icon: Icon, title, description, onClick, isLast }: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`flex w-full items-start gap-4 px-4 py-4 text-left transition active:bg-muted/40 ${
        isLast ? "" : "border-b border-border/60"
      }`}
    >
      <div className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-muted/60 text-foreground/55">
        <Icon className="h-[18px] w-[18px]" strokeWidth={1.6} />
      </div>

      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <h3 className="truncate font-serif text-[16px] leading-tight tracking-tight text-foreground/80">
            {title}
          </h3>
          <span className="flex-none rounded-full border border-border/70 bg-background px-2 py-0.5 text-[10px] uppercase tracking-[0.14em] text-muted-foreground/85">
            В разработке
          </span>
        </div>
        <p className="mt-1 text-[12.5px] leading-relaxed text-muted-foreground">
          {description}
        </p>
      </div>
    </button>
  )
}
