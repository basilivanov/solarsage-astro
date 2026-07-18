// ############################################################################
// AI_HEADER: MODULE_API_RELEASE_HEALTH — frontend release identity route
// ROLE: Returns the frontend container's immutable release identity for the
//       deploy orchestrator; does not shadow the /api/health backend proxy.
// DEPENDENCIES: none (Next.js route handler, runtime env)
// GRACE_ANCHORS: [RELEASE_HEALTH_PAYLOAD]
// ############################################################################

// START_MODULE_CONTRACT: M-API-RELEASE-HEALTH
// purpose: Expose GET /api/release-health returning {status, release_sha}.
// owns:
//   - app/api/release-health/route.ts
// inputs: process.env.RELEASE_SHA (runtime, non-secret)
// outputs: JSON payload with exact release identity.
// dependencies: none
// side_effects: none
// emitted_logs: none
// invariants:
//   - response shape is EXACTLY {status, release_sha}, both string-typed
//   - release_sha comes only from the runtime environment, never from a
//     mutable Git checkout
// failure_policy: release_sha falls back to "unknown" outside the app stack.
// END_MODULE_CONTRACT: M-API-RELEASE-HEALTH

// START_MODULE_MAP: M-API-RELEASE-HEALTH
// public_entrypoints:
//   - GET
// semantic_blocks:
//   - RELEASE_HEALTH_PAYLOAD: assembles and returns the identity payload
// END_MODULE_MAP: M-API-RELEASE-HEALTH

export const dynamic = "force-dynamic";

// START_BLOCK: RELEASE_HEALTH_PAYLOAD
export async function GET() {
  // START_FUNCTION_CONTRACT: F-M-API-RELEASE-HEALTH.GET
  // purpose: Return the frontend release identity for deploy health gating.
  // inputs: none (HTTP GET)
  // returns: Response with EXACTLY {status, release_sha} string fields.
  // side_effects: none.
  // error_behavior: cannot fail under normal operation.
  // END_FUNCTION_CONTRACT: F-M-API-RELEASE-HEALTH.GET
  return Response.json({
    status: "ok",
    release_sha: process.env.RELEASE_SHA || "unknown",
  });
}
// END_BLOCK: RELEASE_HEALTH_PAYLOAD
