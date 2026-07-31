// ############################################################################
// AI_HEADER: TEST_CONTRACTS_SHIMS_SMOKE — feature shim import surface.
// ROLE: Proves every generated contracts feature shim imports cleanly.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-SHIMS-SMOKE
// purpose: Smoke-import all feature shims of packages/contracts.
// owns:
//   - __tests__/contracts/shims-smoke.test.ts
// inputs: packages/contracts/* modules.
// outputs: assertions on exported wire schema presence.
// dependencies: packages/contracts feature shims.
// side_effects: none.
// emitted_logs: none.
// invariants: no network, no fixtures.
// failure_policy: assertion failure on broken shim export.
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-SHIMS-SMOKE

// START_MODULE_MAP: M-TEST-CONTRACTS-SHIMS-SMOKE
// public_entrypoints:
//   - vitest test suite
// semantic_blocks:
//   - IMPORTS: clean import and export presence per shim.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-CONTRACTS-SHIMS-SMOKE

import { describe, expect, it } from "vitest"

// START_BLOCK: IMPORTS
describe("contracts feature shims", () => {
  it("imports every shim without errors", async () => {
    const modules = await Promise.all([
      import("@/packages/contracts/access"),
      import("@/packages/contracts/auth"),
      import("@/packages/contracts/calendar"),
      import("@/packages/contracts/day-history"),
      import("@/packages/contracts/horary"),
      import("@/packages/contracts/natal"),
      import("@/packages/contracts/profile"),
      import("@/packages/contracts/today-sphere-drilldown"),
      import("@/packages/contracts/today-sphere-page"),
      import("@/packages/contracts/today-convergence"),
    ])

    // Runtime (zod) shims must expose a non-empty surface; type-only shims
    // (day-history included) are covered by the clean dynamic import itself.
    const runtimeShims = [
      modules[7], // today-sphere-drilldown
      modules[8], // today-sphere-page
      modules[9], // today-convergence
    ]
    for (const mod of runtimeShims) {
      expect(Object.keys(mod).length).toBeGreaterThan(0)
    }
    expect(modules).toHaveLength(10)
  })
})
// END_BLOCK: IMPORTS
