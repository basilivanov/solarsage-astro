// ############################################################################
// AI_HEADER: ROUTE_DEV_THREE_HORIZON_TIMING_FIXTURE — development-only fixture endpoint.
// ROLE: Serves the browser timing demo only in Next development mode.
// ############################################################################

// START_MODULE_CONTRACT: M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE
// purpose: Expose a local-only fixture endpoint for the browser timing preview.
// owns:
//   - app/api/dev-fixtures/three-horizon-timing/route.ts
// inputs: GET request in NODE_ENV=development.
// outputs: Contract-valid TodayPayload JSON or 404 outside development.
// dependencies: NextResponse; local-host/proxy guards; dynamically imported e2e fixture after all guards.
// side_effects: none.
// emitted_logs: none.
// invariants: fixture import occurs only after development, local-host, and proxy-header guards pass.
// failure_policy: returns 404 when development mode is not active.
// END_MODULE_CONTRACT: M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE

// START_MODULE_MAP: M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE
// public_entrypoints:
//   - GET
// semantic_blocks:
//   - LOCAL_GUARD: reject non-development, public-host, and proxy-origin requests.
//   - FIXTURE_RESPONSE: dynamically load and return the local fixture.
// owned_tests:
//   - __tests__/api/dev-timing-fixture-route.test.ts
// END_MODULE_MAP: M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE

import { NextResponse } from "next/server"
import { hasUnsafeProxyOriginHeaders, isLocalDevHost } from "@/lib/api/dev-auth-guard"

// START_BLOCK: FIXTURE_RESPONSE
export async function GET(request: Request) {
  // START_FUNCTION_CONTRACT: F-M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE.GET
  // purpose: Expose a dev-only HTTP GET endpoint serving the three-horizon timing payload.
  // inputs: HTTP Request object.
  // returns: NextResponse containing JSON payload or 404 error response.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns 404 when access guards reject host, NODE_ENV, or proxy headers; dynamic fixture import/serialization failure is not swallowed and turns into a route error (500).
  // END_FUNCTION_CONTRACT: F-M-ROUTE-DEV-THREE-HORIZON-TIMING-FIXTURE.GET
  if (
    process.env.NODE_ENV !== "development"
    || !isLocalDevHost(request.headers.get("host"))
    || hasUnsafeProxyOriginHeaders(request)
  ) {
    return NextResponse.json({ error: "Not found" }, { status: 404 })
  }

  const { dayPayloadV2 } = await import("../../../../e2e/mock-visual/fixtures/day-v2-2026-07-08")
  return NextResponse.json(dayPayloadV2)
}
// END_BLOCK: FIXTURE_RESPONSE
