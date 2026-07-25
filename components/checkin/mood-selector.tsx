// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_MOOD_SELECTOR
// ROLE: Checkin mood selector component
// DEPENDENCIES: lib/contracts/checkin, lib/utils
// GRACE_ANCHORS: [MOOD_SELECTOR_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-MOOD-SELECTOR
// purpose: Render interactive 5-option checkin mood selector buttons.
// owns:
//   - components/checkin/mood-selector.tsx
// inputs: value (CheckinMood | null), onChange
// outputs: MoodSelector React component
// dependencies: lib/contracts/checkin, lib/utils
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-MOOD-SELECTOR

// START_MODULE_MAP: M-COMPONENTS-MOOD-SELECTOR
// public_entrypoints:
//   - MoodSelector
// semantic_blocks:
//   - MOOD_SELECTOR_COMPONENT: mood selector component
// owned_tests:
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-MOOD-SELECTOR

"use client"

import { MOOD_OPTIONS, type CheckinMood } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  value: CheckinMood | null
  onChange: (mood: CheckinMood) => void
}

// START_BLOCK: MOOD_SELECTOR_COMPONENT
export function MoodSelector({ value, onChange }: Props) {
  return (
    <div className="grid grid-cols-5 gap-2">
      {MOOD_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          data-testid={`mood-${option.value}`}
          onClick={() => onChange(option.value)}
          className={cn(
            "flex min-h-20 flex-col items-center justify-center gap-1 rounded-2xl border px-1 py-3 transition active:scale-[0.98]",
            value === option.value
              ? "border-foreground bg-foreground text-background"
              : "border-border/70 bg-card text-foreground",
          )}
        >
          <span className="text-2xl leading-none">{option.emoji}</span>
          <span className="text-[10px] leading-tight">{option.label}</span>
        </button>
      ))}
    </div>
  )
}
// END_BLOCK: MOOD_SELECTOR_COMPONENT
