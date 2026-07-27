// ############################################################################
// AI_HEADER: MODULE_DAY_COLLAPSIBLE
// ROLE: Reusable disclosure wrapper component for optional Today screen sections.
// DEPENDENCIES: react, lucide-react (ChevronDown)
// GRACE_ANCHORS: [DAY_COLLAPSIBLE]
// ############################################################################

// START_MODULE_CONTRACT: M-DAY-COLLAPSIBLE
// purpose: Provide an accessible, collapsible disclosure container for Today screen progressive details.
// owns:
//   - components/today/day-collapsible.tsx
// inputs: title, dataTestId, children, defaultOpen (optional boolean, default false)
// outputs: Collapsible disclosure JSX section
// dependencies: react, lucide-react
// side_effects: none
// emitted_logs: none
// failure_policy: safe rendering fallback
// END_MODULE_CONTRACT: M-DAY-COLLAPSIBLE

// START_MODULE_MAP: M-DAY-COLLAPSIBLE
// public_entrypoints:
//   - DayCollapsible
// semantic_blocks:
//   - DAY_COLLAPSIBLE_RENDER: render disclosure button and region
// owned_tests:
//   - __tests__/components/TodayScreen.test.tsx
// END_MODULE_MAP: M-DAY-COLLAPSIBLE

"use client"

import React, { useState } from "react"
import { ChevronDown } from "lucide-react"

interface DayCollapsibleProps {
  title: string
  dataTestId: string
  children: React.ReactNode
  defaultOpen?: boolean
}

// START_BLOCK: DAY_COLLAPSIBLE_RENDER
export function DayCollapsible({
  title,
  dataTestId,
  children,
  defaultOpen = false,
}: DayCollapsibleProps) {
  const [open, setOpen] = useState(defaultOpen)

  const toggleId = `${dataTestId}-toggle`
  const regionId = `${dataTestId}-region`

  return (
    <section className="px-5" data-testid={dataTestId}>
      <div className="rounded-[20px] border border-border/60 bg-card overflow-hidden transition-all duration-200">
        <button
          type="button"
          id={toggleId}
          data-testid={toggleId}
          aria-expanded={open}
          aria-controls={regionId}
          onClick={() => setOpen((prev) => !prev)}
          className="w-full flex items-center justify-between px-5 py-4 text-left font-medium text-[15px] text-foreground hover:bg-muted/30 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 transition-colors cursor-pointer"
        >
          <span className="font-semibold">{title}</span>
          <ChevronDown
            className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${
              open ? "rotate-180 text-foreground" : ""
            }`}
            aria-hidden="true"
          />
        </button>

        {open && (
          <div
            id={regionId}
            role="region"
            aria-labelledby={toggleId}
            className="p-4 pt-0 border-t border-border/30"
          >
            {children}
          </div>
        )}
      </div>
    </section>
  )
}
// END_BLOCK: DAY_COLLAPSIBLE_RENDER
