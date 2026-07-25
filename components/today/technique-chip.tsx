// ############################################################################
// AI_HEADER: MODULE_TODAY_TECHNIQUE_CHIP
// ROLE: UI component displaying technique label chip
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-TECHNIQUE-CHIP
// purpose: Render astrological technique label chip.
// owns:
//   - components/today/technique-chip.tsx
// inputs: technique (string)
// outputs: TechniqueChip React component
// dependencies: lib/presentation/today-v2
// side_effects: none (pure rendering)
// emitted_logs: none
// failure_policy: none
// END_MODULE_CONTRACT: M-TODAY-TECHNIQUE-CHIP

// START_MODULE_MAP: M-TODAY-TECHNIQUE-CHIP
// public_entrypoints:
//   - TechniqueChip
// semantic_blocks:
//   - TECHNIQUE_CHIP: Technique label chip component
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-TECHNIQUE-CHIP

import React from "react"
import { getTechniqueLabel } from "@/lib/presentation/today-v2"

interface TechniqueChipProps {
  technique: string
}

// START_BLOCK: TECHNIQUE_CHIP
export function TechniqueChip({ technique }: TechniqueChipProps) {
  const label = getTechniqueLabel(technique)
  return (
    <span
      data-testid="technique-chip"
      title={technique}
      className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-amber-50 text-amber-800 border border-amber-200"
    >
      {label}
    </span>
  )
}
// END_BLOCK: TECHNIQUE_CHIP
