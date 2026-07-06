"use client"

import { TAG_OPTIONS } from "@/lib/contracts/checkin"
import { cn } from "@/lib/utils"

type Props = {
  selected: string[]
  onChange: (tags: string[]) => void
}

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
