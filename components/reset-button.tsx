
// ############################################################################
// AI_HEADER: MODULE_COMPONENTS_RESET_BUTTON
// ROLE: UI component
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: Page: reset-button
// owns:
//   - components/reset-button.tsx
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// public_entrypoints:
//   - ResetButton
// semantic_blocks:
//   - RESET_BUTTON: Reset button component
// owned_tests:
//   - __tests__/components/ProfileScreen.test.tsx
// END_MODULE_MAP

"use client"

import { useRouter } from "next/navigation"

// START_BLOCK: RESET_BUTTON
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
// END_BLOCK: RESET_BUTTON
