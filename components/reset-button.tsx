
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_RESET_BUTTON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: UI component — components/reset-button.tsx
// owns:
//   - components/reset-button.tsx
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

import { useRouter } from "next/navigation"

export function ResetButton() {
  const router = useRouter()

  return (
    <button
      onClick={() => router.push("/reset")}
      className="mt-4 text-xs text-muted-foreground/50 underline hover:text-muted-foreground"
    >
      Сбросить кэш и сессию
    </button>
  )
}
