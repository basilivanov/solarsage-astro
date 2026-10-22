// ############################################################################
// AI_HEADER: APP_HOME_PAGE — root-route server redirect to the canonical day path.
// ROLE: Server Next.js root page; every request is redirected to /day/today without a client bundle.
// GRACE_ANCHORS: [SERVER_REDIRECT]
// ############################################################################

// START_MODULE_CONTRACT: M-APP-HOME-PAGE
// purpose: Keep the root route as a compatibility entry that immediately issues a server redirect to /day/today.
// owns:
//   - app/(grace)/page.tsx
// inputs: route request only.
// outputs: Next redirect response to /day/today; no rendered page body.
// dependencies: next/navigation redirect.
// side_effects: Performs server-side navigation control flow.
// emitted_logs: none.
// invariants:
//   - Every invocation redirects exactly to /day/today.
//   - No client bundle, component mount, auth, data API or logger call is involved.
//   - Route is dynamic server-side, never a statically cached page with a long TTL.
// failure_policy: Next redirect intentionally terminates rendering through framework control flow.
// END_MODULE_CONTRACT: M-APP-HOME-PAGE

// START_MODULE_MAP: M-APP-HOME-PAGE
// public_entrypoints:
//   - HomePage (default).
// semantic_blocks:
//   - SERVER_REDIRECT: issue the canonical root redirect.
// owned_tests:
//   - none direct (verified by production build output and HTTP curl).
// END_MODULE_MAP: M-APP-HOME-PAGE

// START_BLOCK: SERVER_REDIRECT
import { redirect } from "next/navigation"

// Keep the redirect out of the static prerender cache: the root entry must
// never inherit a long-lived s-maxage cache entry.
export const dynamic = "force-dynamic"

export default function HomePage() {
  redirect("/day/today")
}
// END_BLOCK: SERVER_REDIRECT
