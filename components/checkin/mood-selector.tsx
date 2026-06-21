// ############################################################################
// AI_HEADER: MODULE_CHECKIN_MOOD_SELECTOR
// ROLE: UI component — mood selector (5 buttons)
// DEPENDENCIES: react, @/lib/contracts/checkin
// GRACE_ANCHORS: []
// SLICE: SLICE-CHECKIN
// WAVE: W-8.1
// ############################################################################

// START_MODULE_CONTRACT
// purpose: 5-button mood selector for evening checkin.
// owns:
//   - components/checkin/mood-selector.tsx
// inputs: Props (value, onChange)
// outputs: TSX render
// dependencies: @/lib/contracts/checkin
// side_effects: n/a (pure)
// invariants:
//   - 5 options: 😫😕😐🙂🤩
//   - Selected button highlighted
// END_MODULE_CONTRACT

"use client"

import { MOOD_OPTIONS } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: number | null
  onChange: (mood: number) => void
}

export function MoodSelector({ value, onChange }: Props) {
  return (
    <div className="flex justify-between gap-2">
      {MOOD_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          data-testid={`mood-${opt.value}`}
          onClick={() => onChange(opt.value)}
          className={cn(
            "flex flex-1 flex-col items-center gap-1 rounded-2xl border py-3 transition active:scale-95",
            value === opt.value
              ? "border-primary bg-primary/10"
              : "border-border/60 bg-card",
          )}
        >
          <span className="text-2xl">{opt.emoji}</span>
          <span className="text-[10px] text-muted-foreground">{opt.value}</span>
        </button>
      ))}
    </div>
  )
}
