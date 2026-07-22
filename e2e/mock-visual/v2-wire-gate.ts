// ############################################################################
// AI_HEADER: E2E_MOCK_VISUAL_V2_WIRE_GATE — V2 wire identity discriminator.
// ROLE: Single fail-closed predicate deciding whether a committed payload
//       artifact is a coherent today.v2/today.v2.1 wire payload. Shared by
//       the acceptance spec and contract tests (no duplication).
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-V2-WIRE-GATE
// purpose: Discriminate V2 wire identity by meta.payloadVersion plus the
//   coherent meta.frontendPayloadVersion pair and a non-null v2 block.
//   meta.schemaVersion is INTENTIONALLY not used: it is canonically Literal
//   "today/v1" for every payload series (v1 and V2 alike).
// owns:
//   - e2e/mock-visual/v2-wire-gate.ts
// inputs: raw parsed JSON artifact.
// outputs: blocker message string or null (pass).
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - today.v2 pairs with frontendPayloadVersion=2; today.v2.1 with 3.
//   - A V2 identity without a v2 block is a hard blocker.
// failure_policy: returns the blocker reason; callers fail closed.
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-V2-WIRE-GATE

export const V2_FRONTEND_BY_PAYLOAD_VERSION: Readonly<Record<string, number>> = {
  "today.v2": 2,
  "today.v2.1": 3,
}

export function v2WireGateError(rawPayload: unknown): string | null {
  const meta = ((rawPayload as { meta?: Record<string, unknown> } | null)?.meta ?? {}) as Record<string, unknown>
  const payloadVersion = String(meta.payloadVersion ?? "")
  const expectedFrontend = V2_FRONTEND_BY_PAYLOAD_VERSION[payloadVersion]
  if (expectedFrontend === undefined) {
    return `payloadVersion="${payloadVersion}" is not a V2 series (today.v2/today.v2.1)`
  }
  const frontendVersion = meta.frontendPayloadVersion
  if (frontendVersion !== expectedFrontend) {
    return (
      `payloadVersion="${payloadVersion}" requires frontendPayloadVersion=${expectedFrontend}, ` +
      `got ${String(frontendVersion)}`
    )
  }
  if ((rawPayload as { v2?: unknown } | null)?.v2 == null) {
    return `payloadVersion="${payloadVersion}" requires a v2 block`
  }
  return null
}
