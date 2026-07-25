
// ############################################################################
// AI_HEADER: MODULE_PROFILE_SERVICE_ROW
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-PROFILE-ONBOARDING
// ############################################################################
// START_MODULE_CONTRACT: M-PROFILE-SERVICE-ROW
// purpose: Render external link or action row button on Profile screen.
// owns:
//   - components/profile/service-row.tsx
// inputs: icon, label, hint, onClick, disabled, isLast
// outputs: ServiceRow React component
// dependencies: lucide-react, lib/utils
// side_effects: none (pure UI)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-PROFILE-SERVICE-ROW

// START_MODULE_MAP: M-PROFILE-SERVICE-ROW
// public_entrypoints:
//   - ServiceRow
// semantic_blocks:
//   - SERVICE_ROW_COMPONENT: service action row component
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
// END_MODULE_MAP: M-PROFILE-SERVICE-ROW
"use client"

import type { LucideIcon } from "lucide-react"
import { ChevronRight } from "lucide-react"
import { cn } from "@/lib/utils"

type Props = {
  icon: LucideIcon
  label: string
  hint?: string
  onClick?: () => void
  disabled?: boolean
  isLast?: boolean
}

// START_BLOCK: SERVICE_ROW_COMPONENT
export function ServiceRow({
  icon: Icon,
  label,
  hint,
  onClick,
  disabled = false,
  isLast = false,
}: Props) {
  return (
    <button
      type="button"
      onClick={disabled ? undefined : onClick}
      disabled={disabled}
      aria-disabled={disabled}
      className={cn(
        "flex w-full items-center gap-4 px-4 py-3.5 text-left transition active:bg-muted/50 disabled:cursor-not-allowed disabled:opacity-60 disabled:active:bg-transparent",
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
// END_BLOCK: SERVICE_ROW_COMPONENT
