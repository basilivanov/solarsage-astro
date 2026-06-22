// ############################################################################
// AI_HEADER: MODULE_CHECKIN_ACCURACY_SELECTOR
// ROLE: UI component — accuracy selector (3 buttons)
// DEPENDENCIES: react, @/lib/contracts/checkin
// GRACE_ANCHORS: []
// SLICE: SLICE-CHECKIN
// WAVE: W-8.1
// ############################################################################

"use client"

import { ACCURACY_OPTIONS } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: string | null
  onChange: (accuracy: string) => void
}

export function AccuracySelector({ value, onChange }: Props) {
  return (
    <div className="flex gap-2">
      {ACCURACY_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          data-testid={`accuracy-${opt.value}`}
          onClick={() => onChange(opt.value)}
          className={cn(
            "flex flex-1 flex-col items-center gap-1 rounded-2xl border py-3 transition active:scale-95",
            value === opt.value
              ? "border-primary bg-primary/10"
              : "border-border/60 bg-card",
          )}
        >
          <span className="text-xl">{opt.emoji}</span>
          <span className="text-[11px] text-muted-foreground">{opt.label}</span>
        </button>
      ))}
    </div>
  )
}
