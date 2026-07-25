// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_ENERGY_SELECTOR
// ROLE: Checkin energy level selector component
// DEPENDENCIES: lib/contracts/checkin, lib/utils
// GRACE_ANCHORS: [ENERGY_SELECTOR_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-ENERGY-SELECTOR
// purpose: Render interactive 5-option checkin energy level selector buttons.
// owns:
//   - components/checkin/energy-selector.tsx
// inputs: value (CheckinEnergy | null), onChange
// outputs: EnergySelector React component
// dependencies: lib/contracts/checkin, lib/utils
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-ENERGY-SELECTOR

// START_MODULE_MAP: M-COMPONENTS-ENERGY-SELECTOR
// public_entrypoints:
//   - EnergySelector
// semantic_blocks:
//   - ENERGY_SELECTOR_COMPONENT: energy selector component
// owned_tests:
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-ENERGY-SELECTOR

"use client"

import { ENERGY_OPTIONS, type CheckinEnergy } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: CheckinEnergy | null
  onChange: (energy: CheckinEnergy) => void
}

// START_BLOCK: ENERGY_SELECTOR_COMPONENT
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
// END_BLOCK: ENERGY_SELECTOR_COMPONENT
