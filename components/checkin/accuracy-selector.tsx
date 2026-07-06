"use client"

import { ACCURACY_OPTIONS, type CheckinAccuracy } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: CheckinAccuracy | null
  onChange: (accuracy: CheckinAccuracy) => void
}

export function AccuracySelector({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-3 gap-2">
      {ACCURACY_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          data-testid={`accuracy-${option.value}`}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex min-h-20 flex-col items-center justify-center gap-1 rounded-2xl border px-2 py-3 transition active:scale-[0.98]",
            value === option.value
              ? "border-foreground bg-foreground text-background"
              : "border-border/70 bg-card text-foreground",
          )}
        >
          <span className="text-xl leading-none">{option.emoji}</span>
          <span className="text-center text-[11px] leading-tight">{option.label}</span>
        </button>
      ))}
    </div>
  )
}
