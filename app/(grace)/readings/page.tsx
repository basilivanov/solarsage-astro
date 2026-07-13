
// ############################################################################
// AI_HEADER: APP_READINGS_PAGE — readings catalogue route wrapper.
// ROLE: Client Next.js page called by /readings; delegates catalogue UI and navigation to ReadingsScreen.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-READINGS-PAGE
// purpose: Expose the canonical readings catalogue without duplicating screen logic.
// owns:
//   - app/(grace)/readings/page.tsx
// inputs: none at page level.
// outputs: ReadingsScreen.
// dependencies: ReadingsScreen.
// side_effects: none at page level; delegated to ReadingsScreen.
// emitted_logs: none at page level.
// invariants:
//   - Route remains a thin wrapper around ReadingsScreen.
// failure_policy: Screen/render failures are delegated to ReadingsScreen and the route boundary.
// END_MODULE_CONTRACT: M-APP-READINGS-PAGE

// START_MODULE_MAP: M-APP-READINGS-PAGE
// public_entrypoints:
//   - ReadingsPage (default).
// semantic_blocks:
//   - PAGE_COMPOSITION: render ReadingsScreen.
// owned_tests:
//   - none direct.
// END_MODULE_MAP: M-APP-READINGS-PAGE
'use client'

import { ReadingsScreen } from "@/components/readings/readings-screen"

/** /readings — список разборов. */
export default function ReadingsPage() {
  return <ReadingsScreen />
}
