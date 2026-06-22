
// ############################################################################
// AI_HEADER: MODULE_HORARY_PAGE
// ROLE: Next.js page
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################
// START_MODULE_CONTRACT
// purpose: UI page — component
// owns:
//   - app/(grace)/readings/horary/page.tsx
// inputs: Component props / hook params
// outputs: TSX render / values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
"use client"

import { HoraryScreen } from "@/components/readings/horary/horary-screen"

export default function HoraryPage() {
  return <HoraryScreen />
}
