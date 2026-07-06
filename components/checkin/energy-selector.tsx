"use client"

import { ENERGY_OPTIONS, type CheckinEnergy } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: CheckinEnergy | null
  onChange: (energy: CheckinEnergy) => void
}

export function EnergySelector({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {ENERGY_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          data-testid={`energy-${option.value}`}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex min-h-20 flex-col items-center justify-center gap-1 rounded-2xl border px-1 py-3 transition active:scale-[0.98]",
            value === option.value
              ? "border-foreground bg-foreground text-background"
              : "border-border/70 bg-card text-foreground",
          )}
        >
          <span className="text-2xl leading-none">{option.emoji}</span>
          <span className="text-center text-[10px] leading-tight">{option.label}</span>
        </button>
      ))}
    </div>
  )
}
