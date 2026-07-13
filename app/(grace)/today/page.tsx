// ############################################################################
// AI_HEADER: APP_TODAY_REDIRECT_PAGE — legacy /today compatibility redirect.
// ROLE: Server Next.js page called by /today; redirects all requests to the canonical migrated /day/today route.
// ############################################################################

// START_MODULE_CONTRACT: M-APP-TODAY-REDIRECT-PAGE
// purpose: Preserve old /today links while maintaining one canonical real-data day route.
// owns:
//   - app/(grace)/today/page.tsx
// inputs: route request only.
// outputs: Next redirect response to /day/today; no rendered page body.
// dependencies: next/navigation redirect.
// side_effects: Performs server-side navigation control flow.
// emitted_logs: none.
// invariants:
//   - Every invocation redirects exactly to /day/today.
//   - Route contains no fixture, auth, API or rendering branch.
// failure_policy: Next redirect intentionally terminates rendering through framework control flow.
// END_MODULE_CONTRACT: M-APP-TODAY-REDIRECT-PAGE

// START_MODULE_MAP: M-APP-TODAY-REDIRECT-PAGE
// public_entrypoints:
//   - TodayPage (default).
// semantic_blocks:
//   - COMPATIBILITY_REDIRECT: issue the canonical redirect.
// owned_tests:
//   - __tests__/app/today-redirect.test.ts
//   - __tests__/grace-discipline.test.ts
// END_MODULE_MAP: M-APP-TODAY-REDIRECT-PAGE

import { redirect } from "next/navigation"

export default function TodayPage() {
  redirect("/day/today")
}
