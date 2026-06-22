// START_MODULE_CONTRACT: M-LIB-PRODUCTION-GUARD
// purpose: Validate production environment safety against unsafe demo configurations.
// owns:
//   - lib/env/production-guard.mjs
// inputs:
//   - process.env.NEXT_PUBLIC_DEMO_MODE
//   - process.env.ALLOW_DEMO_MODE_IN_PREVIEW
//   - process.env.VERCEL_ENV / APP_ENV / NODE_ENV
// outputs:
//   - void (throws on violation)
// dependencies:
//   - none (pure ESM)
// side_effects:
//   - reads process.env
//   - may throw Error on unsafe config
// invariants:
//   - throws if NEXT_PUBLIC_DEMO_MODE=true in production
//   - throws if NEXT_PUBLIC_DEMO_MODE=true in preview without ALLOW_DEMO_MODE_IN_PREVIEW
// failure_policy:
//   - throws Error on unsafe config; never silently passes
// END_MODULE_CONTRACT: M-LIB-PRODUCTION-GUARD

// START_MODULE_MAP: M-LIB-PRODUCTION-GUARD
// public_entrypoints:
//   - assertProductionSafety
// semantic_blocks:
//   - SAFETY_CHECK: environment validation
// END_MODULE_MAP: M-LIB-PRODUCTION-GUARD

// ############################################################################
// AI_HEADER: MODULE_PRODUCTION_GUARD
// ROLE: Ensure production environment safety against unsafe demo configurations.
// DEPENDENCIES: none (pure JS/ESM)
// GRACE_ANCHORS: [SAFETY_CHECK]
// ############################################################################

 

/* START_BLOCK: SAFETY_CHECK */
export function assertProductionSafety() {
  const demoMode = process.env.NEXT_PUBLIC_DEMO_MODE === "true";
  const allowPreview = process.env.ALLOW_DEMO_MODE_IN_PREVIEW === "true";
  // Use NEXT_PUBLIC_APP_ENV so the value is inlined into the client bundle
  // at build time and available in the browser. Plain APP_ENV is server-only.
  const deploymentEnv = process.env.NEXT_PUBLIC_APP_ENV || process.env.VERCEL_ENV || process.env.APP_ENV || "";

  const isPreview = deploymentEnv === "preview" || deploymentEnv === "staging";
  const isExplicitDev = deploymentEnv === "dev" || deploymentEnv === "test";
  const isExplicitProd = deploymentEnv === "production" || (!isPreview && !isExplicitDev && process.env.NODE_ENV === "production");

  if (isPreview && demoMode && !allowPreview) {
    throw new Error(
      "Unsafe preview config: NEXT_PUBLIC_DEMO_MODE=true requires ALLOW_DEMO_MODE_IN_PREVIEW=true in preview/staging"
    );
  }

  if (isExplicitProd && demoMode) {
    throw new Error(
      "Unsafe production config: NEXT_PUBLIC_DEMO_MODE=true is forbidden in production"
    );
  }

  if (demoMode) {
    console.warn("[GUARD] Demo mode enabled");
  }
}
/* END_BLOCK: SAFETY_CHECK */
