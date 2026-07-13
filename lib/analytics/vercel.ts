// ############################################################################
// AI_HEADER: MODULE_LIB_ANALYTICS_VERCEL — deployment-boundary Vercel Analytics gate.
// ROLE: Server-only helper that decides whether to render @vercel/analytics.
// DEPENDENCIES: none (pure function, no framework imports).
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-ANALYTICS-VERCEL
// purpose: Expose one pure function that returns true only when the app is
//   running in an actual Vercel production deployment (NODE_ENV=production AND
//   VERCEL=1). Self-hosted production, development, and test environments all
//   return false.
// owns:
//   - lib/analytics/vercel.ts
// inputs: EnvInput — explicit object with optional NODE_ENV and VERCEL strings.
// outputs: boolean — should Vercel Analytics render.
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Treats VERCEL=1 (exact string) as the only positive indicator.
//   - VERCEL=0, VERCEL absent, VERCEL malformed all return false.
// failure_policy: returns false for any unrecognised input; never throws.
// END_MODULE_CONTRACT: M-LIB-ANALYTICS-VERCEL

// START_MODULE_MAP: M-LIB-ANALYTICS-VERCEL
// public_entrypoints:
//   - shouldRenderVercelAnalytics
// semantic_blocks:
//   - VERCEL_ANALYTICS_GATE
// owned_tests:
//   - __tests__/lib/vercel-analytics.test.ts
// END_MODULE_MAP: M-LIB-ANALYTICS-VERCEL

// START_BLOCK: VERCEL_ANALYTICS_GATE
export interface EnvInput {
  NODE_ENV?: string
  VERCEL?: string
}

/**
 * Determine whether @vercel/analytics should render.
 *
 * Truth table:
 *   NODE_ENV=production and VERCEL=1  => true
 *   NODE_ENV=production and VERCEL absent => false
 *   NODE_ENV=production and VERCEL=0  => false
 *   NODE_ENV=development and VERCEL=1 => false
 *   NODE_ENV=test and VERCEL=1        => false
 *   malformed/partial input           => false
 */
export function shouldRenderVercelAnalytics(env: EnvInput): boolean {
  // START_FUNCTION_CONTRACT: F-M-LIB-ANALYTICS-VERCEL.shouldRenderVercelAnalytics
  // purpose: Return true only for genuine Vercel production deployments.
  // inputs: env — object with optional NODE_ENV and VERCEL keys.
  // returns: boolean — true iff NODE_ENV === "production" and VERCEL === "1".
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns false for all unrecognised input; never throws.
  // END_FUNCTION_CONTRACT: F-M-LIB-ANALYTICS-VERCEL.shouldRenderVercelAnalytics
  return env.NODE_ENV === "production" && env.VERCEL === "1"
}

/**
 * Convenience wrapper that reads from process.env.
 * Kept separate so tests can inject explicit EnvInput without mutating globals.
 */
export function shouldRenderVercelAnalyticsFromEnv(): boolean {
  return shouldRenderVercelAnalytics({
    NODE_ENV: process.env.NODE_ENV,
    VERCEL: process.env.VERCEL,
  })
}
// END_BLOCK: VERCEL_ANALYTICS_GATE
