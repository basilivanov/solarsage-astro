// ############################################################################
// AI_HEADER: APP_ELECTION_PAGE
// ROLE: Main election reading page
// ############################################################################

// START_MODULE_CONTRACT: M-APP-ELECTION-PAGE
// purpose: Route entrypoint that mounts the election reading screen.
// owns:
//   - app/(grace)/readings/election/page.tsx
// inputs: none (Next.js route segment).
// outputs: ElectionScreen React component tree.
// dependencies: components/readings/election/election-screen.
// side_effects: none (delegated to ElectionScreen).
// emitted_logs: none.
// invariants: route only composes ElectionScreen without additional state.
// failure_policy: render errors propagate to the route error boundary.
// END_MODULE_CONTRACT: M-APP-ELECTION-PAGE

// START_MODULE_MAP: M-APP-ELECTION-PAGE
// public_entrypoints:
//   - ElectionPage (default)
// semantic_blocks:
//   - PAGE_COMPOSITION: render ElectionScreen.
// owned_tests:
//   - e2e/readings-election.spec.ts
// END_MODULE_MAP: M-APP-ELECTION-PAGE

import { ElectionScreen } from "@/components/readings/election/election-screen"

export default function ElectionPage() {
  return <ElectionScreen />
}
