
// ############################################################################
// AI_HEADER: APP_HORARY_PAGE — horary question flow route wrapper.
// ROLE: Client Next.js page called by /readings/horary; delegates the complete interactive flow to HoraryScreen.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-HORARY-PAGE
// purpose: Expose HoraryScreen at the canonical horary route without duplicating its business logic.
// owns:
//   - app/(grace)/readings/horary/page.tsx
// inputs: none at page level.
// outputs: HoraryScreen.
// dependencies: HoraryScreen.
// side_effects: none at page level; delegated to HoraryScreen.
// emitted_logs: none at page level.
// invariants:
//   - Route remains a thin wrapper around the canonical HoraryScreen.
// failure_policy: Flow/render failures are delegated to HoraryScreen and the route boundary.
// END_MODULE_CONTRACT: M-APP-HORARY-PAGE

// START_MODULE_MAP: M-APP-HORARY-PAGE
// public_entrypoints:
//   - HoraryPage (default).
// semantic_blocks:
//   - PAGE_COMPOSITION: render HoraryScreen.
// owned_tests:
//   - __tests__/horary/horary-screen-flow.test.tsx (indirect flow coverage).
// END_MODULE_MAP: M-APP-HORARY-PAGE
"use client"

import { HoraryScreen } from "@/components/readings/horary/horary-screen"

export default function HoraryPage() {
  return <HoraryScreen />
}
