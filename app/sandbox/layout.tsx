// ############################################################################
// AI_HEADER: MODULE_SANDBOX_LAYOUT — dev-only prototype sandbox guard and frame.
// ROLE: Gates /sandbox/* to development mode and provides a neutral page frame.
// ############################################################################

// START_MODULE_CONTRACT: M-SANDBOX-LAYOUT
// purpose: Make prototype previews available only on dev servers, never in production runtime.
// owns:
//   - app/sandbox/layout.tsx
// inputs: nested sandbox routes.
// outputs: children in development; 404 everywhere else.
// dependencies: next/navigation notFound.
// side_effects: none.
// emitted_logs: none.
// invariants: production builds never expose /sandbox content.
// failure_policy: notFound() outside development.
// END_MODULE_CONTRACT: M-SANDBOX-LAYOUT

// START_MODULE_MAP: M-SANDBOX-LAYOUT
// public_entrypoints:
//   - SandboxLayout
// semantic_blocks:
//   - DEV_GUARD: environment gate for the whole subtree.
// owned_tests:
//   - none (dev tooling; visual check via sandbox flow)
// END_MODULE_MAP: M-SANDBOX-LAYOUT

import { notFound } from "next/navigation";

// START_BLOCK: DEV_GUARD
export default function SandboxLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV !== "development") notFound();
  return children;
}
// END_BLOCK: DEV_GUARD
