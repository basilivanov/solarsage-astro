// START_MODULE_CONTRACT
// purpose: Library: production-guard.mjs
// owns:
//   - lib/env/production-guard.mjs
// inputs: Function args
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

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
  const deploymentEnv = process.env.VERCEL_ENV || process.env.APP_ENV || "";

  const isPreview = deploymentEnv === "preview" || deploymentEnv === "staging";
  const isExplicitProd = deploymentEnv === "production" || (!isPreview && process.env.NODE_ENV === "production");

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
    console.warn("[GUARD] Demo mode enabled");// START_MODULE_CONTRACT
// purpose: Library: production-guard.mjs
// owns:
//   - lib/env/production-guard.mjs
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
  const deploymentEnv = process.env.VERCEL_ENV || process.env.APP_ENV || "";

  const isPreview = deploymentEnv === "preview" || deploymentEnv === "staging";
  const isExplicitProd = deploymentEnv === "production" || (!isPreview && process.env.NODE_ENV === "production");

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
