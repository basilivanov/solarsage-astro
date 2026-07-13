// ############################################################################
// AI_HEADER: TEST_CONTRACTS_TODAY_REDECLARATION — guardrail test to prevent raw wire schema redeclarations.
// ROLE: Scans lib/contracts/today.ts to ensure manual zod schemas for raw V2 fields do not creep back.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-REDECLARATION
// purpose: Prevent manual duplication of wire schemas in lib/contracts/today.ts.
// owns:
//   - __tests__/contracts/today-redeclaration-guard.test.ts
// inputs: file contents of lib/contracts/today.ts
// outputs: vitest assertions
// dependencies: fs, path
// side_effects: none
// emitted_logs: none
// invariants:
//   - lib/contracts/today.ts must not define raw wire schemas manually using z.object.
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-REDECLARATION

// START_MODULE_MAP: M-TEST-CONTRACTS-TODAY-REDECLARATION
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - REDECLARATION_GUARD_TESTS: validates forbidden zod schema patterns
// owned_tests:
//   - __tests__/contracts/today-redeclaration-guard.test.ts
// END_MODULE_MAP: M-TEST-CONTRACTS-TODAY-REDECLARATION

import { describe, expect, it } from "vitest"
import fs from "node:fs"
import path from "node:path"

describe("today contract redeclaration guard", () => {
  // START_BLOCK: REDECLARATION_GUARD_TESTS
  it("prohibits manual raw wire schema object redeclarations in lib/contracts/today.ts", () => {
    const filePath = path.resolve(__dirname, "../../lib/contracts/today.ts")
    const content = fs.readFileSync(filePath, "utf8")

    const forbiddenSchemas = [
      "ActivationEvidenceSchema",
      "SphereContributionSchema",
      "SphereScoreV2Schema",
      "TodayV2ActivatedTargetSchema",
      "TodayV2ActivationSummarySchema",
      "TodayV2WhyTodayItemSchema",
      "TodayV2AuditSchema",
      "TodayV2BlockSchema",
    ]

    for (const schemaName of forbiddenSchemas) {
      // We look for patterns like: export const ActivationEvidenceSchema = z.object(
      // But allow TodayV2BlockSchema = TodayV2BlockWireSchema
      const regex = new RegExp(`export\\s+const\\s+${schemaName}\\s*=\\s*z\\.object`)
      expect(regex.test(content)).toBe(false)
    }
  })
  // END_BLOCK: REDECLARATION_GUARD_TESTS
})
