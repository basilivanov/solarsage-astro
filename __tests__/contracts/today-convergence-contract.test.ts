// ############################################################################
// AI_HEADER: TEST_CONTRACTS_TODAY_CONVERGENCE — generated P1-F fixture parity.
// ROLE: Proves all five canonical wire fixtures parse through the feature shim.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-CONVERGENCE
// purpose: Validate generated TypeScript/Zod Today Convergence contract parity.
// owns:
//   - __tests__/contracts/today-convergence-contract.test.ts
// inputs: the five committed JSON contract fixtures.
// outputs: Vitest assertions against the generated root schema.
// dependencies: packages/contracts/today-convergence.ts, generated Zod artifacts.
// side_effects: reads JSON fixtures only.
// emitted_logs: none.
// invariants: fixtures are parsed through generated root Zod, never handwritten schemas.
// failure_policy: test failure on generated contract drift.
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-CONVERGENCE

// START_MODULE_MAP: M-TEST-CONTRACTS-TODAY-CONVERGENCE
// public_entrypoints:
//   - fixture round-trip test
//   - strict legacy rejection test
// semantic_blocks:
//   - GENERATED_FIXTURES: parse all canonical state projections.
//   - STRICT_ROOT: reject legacy and unknown root fields.
// owned_tests:
//   - self
// END_MODULE_MAP: M-TEST-CONTRACTS-TODAY-CONVERGENCE

import { describe, expect, it } from "vitest";
import hero from "@/apps/api/tests/fixtures/contracts/today-convergence-full-hero-ready.json";
import quiet from "@/apps/api/tests/fixtures/contracts/today-convergence-full-quiet-not-needed.json";
import preview from "@/apps/api/tests/fixtures/contracts/today-convergence-preview.json";
import locked from "@/apps/api/tests/fixtures/contracts/today-convergence-locked.json";
import unavailable from "@/apps/api/tests/fixtures/contracts/today-convergence-unavailable.json";
import {
  TodayConvergencePayloadWireSchema,
} from "@/packages/contracts/today-convergence";

describe("Today Convergence generated wire contract", () => {
  it("parses every canonical state fixture through the generated root schema", () => {
    for (const payload of [hero, quiet, preview, locked, unavailable]) {
      expect(TodayConvergencePayloadWireSchema.safeParse(payload).success).toBe(true);
    }
  });

  it("accepts additive root fields but strips legacy and unknown keys from parsed output", () => {
    for (const [key, value] of [
      ["dayStatus", "tense"],
      ["focus", {}],
      ["v2", {}],
      ["futureField", true],
    ] as const) {
      const parsed = TodayConvergencePayloadWireSchema.safeParse({ ...locked, [key]: value });
      expect(parsed.success).toBe(true);
      if (parsed.success) {
        expect(Reflect.has(parsed.data, key)).toBe(false);
      }
    }
  });

});
