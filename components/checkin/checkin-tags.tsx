// ############################################################################
// AI_HEADER: MODULE_CHECKIN_TAGS
// ROLE: UI component — tag selector (closed set)
// DEPENDENCIES: react, @/lib/contracts/checkin
// GRACE_ANCHORS: []
// SLICE: SLICE-CHECKIN
// WAVE: W-8.1
// ############################################################################

"use client"

import { TAG_OPTIONS, type CheckinTag } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  selected: string[]
  onChange: (tags: string[]) => void
}

export function CheckinTags({ selected, onChange }: Props) {
  const toggle = (tag: string) => {
    if (selected.includes(tag)) {
      onChange(selected.filter((t) => t !== tag))
    } else {
      onChange([...selected, tag])
    }
  }

  return (
    <div className="flex flex-wrap gap-2">
      {TAG_OPTIONS.map((opt) => (
        <button
          key={opt.value}
          type="button"
          data-testid={`tag-${opt.value}`}
          onClick={() => toggle(opt.value)}
          className={cn(
            "flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-[12px] transition active:scale-95",
            selected.includes(opt.value)
              ? "border-primary bg-primary/10 text-primary"
              : "border-border/60 bg-card text-muted-foreground",
          )}
        >
          <span>{opt.emoji}</span>
          <span>{opt.label}</span>
        </button>
      ))}
    </div>
  )
}
