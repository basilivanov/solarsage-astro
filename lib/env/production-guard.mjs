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
