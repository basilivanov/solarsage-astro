// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_CHECKIN_TAGS
// ROLE: Checkin tags selector component
// DEPENDENCIES: lib/contracts/checkin, lib/utils
// GRACE_ANCHORS: [CHECKIN_TAGS_COMPONENT]
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-TAGS
// purpose: Render multi-select tag buttons for checkin entry.
// owns:
//   - components/checkin/checkin-tags.tsx
// inputs: selected (string[]), onChange
// outputs: CheckinTags React component
// dependencies: lib/contracts/checkin, lib/utils
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-COMPONENTS-CHECKIN-TAGS

// START_MODULE_MAP: M-COMPONENTS-CHECKIN-TAGS
// public_entrypoints:
//   - CheckinTags
// semantic_blocks:
//   - CHECKIN_TAGS_COMPONENT: checkin tags component
// owned_tests:
//   - __tests__/components/CheckinScreen.test.tsx
// END_MODULE_MAP: M-COMPONENTS-CHECKIN-TAGS

"use client"

import { TAG_OPTIONS } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  selected: string[]
  onChange: (tags: string[]) => void
}

// START_BLOCK: CHECKIN_TAGS_COMPONENT
export function CheckinTags({ selected, onChange }: Props) {
  const toggle = (tag: string) => {
    onChange(
      selected.includes(tag)
        ? selected.filter((item) => item !== tag)
        : [...selected, tag],
    )
  }

  return (
    <div className="flex flex-wrap gap-2">
      {TAG_OPTIONS.map((option) => (
        <button
          key={option.value}
          type="button"
          data-testid={`tag-${option.value}`}
          onClick={() => toggle(option.value)}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] transition active:scale-[0.98]",
            selected.includes(option.value)
              ? "border-foreground bg-foreground text-background"
              : "border-border/70 bg-card text-muted-foreground",
          )}
        >
          <span>{option.emoji}</span>
          <span>{option.label}</span>
        </button>
      ))}
    </div>
  )
}
// END_BLOCK: CHECKIN_TAGS_COMPONENT
