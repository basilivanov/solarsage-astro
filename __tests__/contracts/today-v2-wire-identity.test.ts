// ############################################################################
// AI_HEADER: TEST_TODAY_V2_WIRE_IDENTITY — V2 wire gate contract (TS side).
// ROLE: Proves the acceptance discriminator: committed V2 fixture passes the
//       gate and the canonical wire schema with schemaVersion "today/v1";
//       v1 payloadVersion, incoherent frontend pair and missing v2 block are
//       rejected by the SAME predicate the acceptance spec uses.
// ############################################################################

import { readFileSync } from "node:fs"
import { describe, expect, it } from "vitest"

import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
import { v2WireGateError } from "../../e2e/mock-visual/v2-wire-gate"

const FIXTURE_PATH = "e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json"
const fixture = JSON.parse(readFileSync(FIXTURE_PATH, "utf-8")) as {
  meta: Record<string, unknown>
  v2?: unknown
}

function withMeta(patch: Record<string, unknown>): unknown {
  return { ...fixture, meta: { ...fixture.meta, ...patch } }
}

describe("today V2 wire identity gate", () => {
  it("committed V2.1 fixture passes the gate and the canonical wire schema", () => {
    expect(v2WireGateError(fixture)).toBeNull()
    // schemaVersion is canonically "today/v1" for ALL series — never the discriminator.
    expect(fixture.meta.schemaVersion).toBe("today/v1")
    expect(fixture.meta.payloadVersion).toBe("today.v2.1")
    expect(fixture.meta.frontendPayloadVersion).toBe(3)
    expect(fixture.v2).not.toBeNull()
    const parsed = TodayPayloadWireSchema.parse(fixture)
    expect(parsed.meta.payloadVersion).toBe("today.v2.1")
  })

  it("rejects today.v1 payloadVersion (the old snake artifact class)", () => {
    const v1 = withMeta({ payloadVersion: "today.v1", frontendPayloadVersion: 1 })
    const error = v2WireGateError(v1)
    expect(error).not.toBeNull()
    expect(error).toContain("not a V2 series")
  })

  it("rejects an incoherent frontend pair for the current V2 identity", () => {
    const incoherent = withMeta({ frontendPayloadVersion: 2 })
    const error = v2WireGateError(incoherent)
    expect(error).not.toBeNull()
    expect(error).toContain("frontendPayloadVersion=3")
  })

  it("rejects a V2 identity without a v2 block", () => {
    const noBlock = { ...fixture, v2: null }
    const error = v2WireGateError(noBlock)
    expect(error).not.toBeNull()
    expect(error).toContain("requires a v2 block")
  })
})
