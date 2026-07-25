// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_ACCURACY_SELECTOR
// ROLE: Checkin accuracy selector component
// DEPENDENCIES: lib/contracts/checkin, lib/utils
// GRACE_ANCHORS: [ACCURACY_SELECTOR_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-ACCURACY-SELECTOR
// purpose: Render interactive 3-option checkin accuracy selector buttons.
// owns:
//   - components/checkin/accuracy-selector.tsx
// inputs: value (CheckinAccuracy | null), onChange
// outputs: AccuracySelector React component
// dependencies: lib/contracts/checkin, lib/utils
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-ACCURACY-SELECTOR

// START_MODULE_MAP: M-COMPONENTS-ACCURACY-SELECTOR
// public_entrypoints:
//   - AccuracySelector
// semantic_blocks:
//   - ACCURACY_SELECTOR_COMPONENT: accuracy selector component
// owned_tests:
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-ACCURACY-SELECTOR

"use client"

import { ACCURACY_OPTIONS, type CheckinAccuracy } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: CheckinAccuracy | null
  onChange: (accuracy: CheckinAccuracy) => void
}

// START_BLOCK: ACCURACY_SELECTOR_COMPONENT
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
// END_BLOCK: ACCURACY_SELECTOR_COMPONENT
