
// ############################################################################
// AI_HEADER: MODULE_PROFILE_SERVICE_ROW
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/profile/service-row.tsx
// owns:
//   - components/profile/service-row.tsx
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

"use client"

import type { LucideIcon } from "lucide-react"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  icon: LucideIcon
  label: string
  hint?: string
  onClick?: () => void
  isLast?: boolean
}

export function ServiceRow({
  icon: Icon,
  label,
  hint,
  onClick,
  isLast = false,
}: Props) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "flex w-full items-center gap-4 px-4 py-3.5 text-left transition active:bg-muted/50",
        !isLast && "border-b border-border/55",
      )}
    >
      <Icon
        className="h-[18px] w-[18px] flex-none text-foreground/70"
        strokeWidth={1.75}
      />
      <div className="min-w-0 flex-1">
        <div className="truncate text-[14.5px] font-medium leading-snug text-foreground">
          {label}
        </div>
        {hint ? (
          <div className="mt-0.5 truncate text-[12.5px] leading-snug text-muted-foreground">
            {hint}
          </div>
        ) : null}
      </div>
      <ChevronRight
        className="h-4 w-4 flex-none text-muted-foreground/60"
        strokeWidth={1.75}
      />
    </button>
  )
}
