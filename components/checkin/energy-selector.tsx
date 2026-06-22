"use client"

import { ENERGY_OPTIONS } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: number | null
  onChange: (_energy: number) => void
}

export function EnergySelector({ value, onChange }: Props) {
  return (
    <div className="flex justify-between gap-2">
      {ENERGY_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          data-testid={`energy-${opt.value}`}
          onClick={() => onChange(opt.value)}
          className={cn(
            "flex flex-1 flex-col items-center gap-1 rounded-2xl border py-3 transition active:scale-95",
            value === opt.value
              ? "border-primary bg-primary/10"
              : "border-border/60 bg-card",
          )}
        >
          <span className="text-2xl">{opt.emoji}</span>
          <span className="text-[9px] leading-tight text-muted-foreground text-center px-0.5">
            {opt.label}
          </span>
        </button>
      ))}
    </div>
  )
}
