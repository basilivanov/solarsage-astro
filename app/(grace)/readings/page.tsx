
// ############################################################################
// AI_HEADER: MODULE_READINGS_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Next.js page — app/(grace)/readings/page.tsx
// owns:
//   - app/(grace)/readings/page.tsx
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

'use client'

import { ReadingsScreen } from "@/components/readings/readings-screen"

/** /readings — список разборов. */
export default function ReadingsPage() {
  return <ReadingsScreen />
}
