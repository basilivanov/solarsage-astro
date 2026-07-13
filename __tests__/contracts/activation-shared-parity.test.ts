// ############################################################################
// AI_HEADER: TEST_CONTRACTS_ACTIVATION_SHARED_PARITY — generated Zod activation fixture parity
// ROLE: Proves generated ActivationLayer Zod schema accepts the shared public camel fixture.
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-ACTIVATION-SHARED-PARITY
// purpose: Validate generated ActivationLayer runtime schema against the canonical public camel fixture.
// owns:
//   - __tests__/contracts/activation-shared-parity.test.ts
// inputs: apps/api/tests/fixtures/contracts/activation-layer-public-camel.json, generated Zod schema.
// outputs: Vitest assertions.
// dependencies: vitest, packages/contracts/_generated.zod.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - Public activation layer fixture remains parseable by generated Zod.
//   - Required nested id and typed timing fields remain enforced.
// failure_policy: vitest failure.
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-ACTIVATION-SHARED-PARITY

// START_MODULE_MAP: M-TEST-CONTRACTS-ACTIVATION-SHARED-PARITY
// public_entrypoints:
//   - describe/it blocks
// semantic_blocks:
//   - ACTIVATION_PARITY_TESTS: generated Zod parsing and rejection checks
// owned_tests:
//   - __tests__/contracts/activation-shared-parity.test.ts
// END_MODULE_MAP: M-TEST-CONTRACTS-ACTIVATION-SHARED-PARITY

// START_BLOCK: ACTIVATION_PARITY_TESTS
import { describe, expect, it } from "vitest"
import fixture from "@/apps/api/tests/fixtures/contracts/activation-layer-public-camel.json"
import { ActivationLayer } from "@/packages/contracts/_generated.zod"

function cloneFixture(): Record<string, unknown> {
  return JSON.parse(JSON.stringify(fixture))
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value)
}

function activationRows(value: Record<string, unknown>): Array<Record<string, unknown>> {
  const rows = value.activations
  if (!Array.isArray(rows) || !rows.every(isRecord)) {
    throw new Error("fixture activations must be records")
  }
  return rows
}

describe("activation shared generated zod parity", () => {
  it("parses the canonical public camel fixture", () => {
    const parsed = ActivationLayer.safeParse(fixture)
    expect(parsed.success).toBe(true)
  })

  it("rejects missing required nested id", () => {
    const malformed = cloneFixture()
    const rows = activationRows(malformed)
    delete rows[0].id
    const parsed = ActivationLayer.safeParse(malformed)
    expect(parsed.success).toBe(false)
  })

  it("rejects wrong activeFrom type", () => {
    const malformed = cloneFixture()
    const rows = activationRows(malformed)
    rows[0].activeFrom = 123
    const parsed = ActivationLayer.safeParse(malformed)
    expect(parsed.success).toBe(false)
  })

  it("keeps date-only period bounds as strings", () => {
    const parsed = ActivationLayer.parse(fixture)
    expect(parsed.activations[1]?.activeFrom).toBe("2025-10-30")
    expect(parsed.activations[1]?.activeUntil).toBe("2026-10-29")
  })
})
// END_BLOCK: ACTIVATION_PARITY_TESTS
