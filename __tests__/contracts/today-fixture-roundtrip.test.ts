// ############################################################################
// AI_HEADER: TEST_CONTRACTS_TODAY_FIXTURE_ROUNDTRIP
// ROLE: Frontend round-trip and single-source validator tests for visual fixture.
// DEPENDENCIES: local modules, packages/contracts, packages/contracts/runtime
// ############################################################################

// START_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-FIXTURE-ROUNDTRIP
// purpose: Prove that day-v2-2026-07-08 visual fixture complies with Zod schemas and has consistent V2 evidence ids.
// owns:
//   - __tests__/contracts/today-fixture-roundtrip.test.ts
// inputs: e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
// outputs: vitest assertions
// dependencies: packages/contracts, packages/contracts/runtime, lib/adapters/today-payload
// side_effects: none
// emitted_logs: none
// invariants:
//   - every referenced V2 activation ID must exist in evidence set
//   - ts wrapper must import exact JSON path and not duplicate headline
// failure_policy: fail test
// END_MODULE_CONTRACT: M-TEST-CONTRACTS-TODAY-FIXTURE-ROUNDTRIP

// START_MODULE_MAP: M-TEST-CONTRACTS-TODAY-FIXTURE-ROUNDTRIP
// public_entrypoints: describe/it blocks
// semantic_blocks:
//   - FIXTURE_ROUNDTRIP: validates zod parser, wrapper payload, activation IDs, and timing map consistency.
// owned_tests:
//   - __tests__/contracts/today-fixture-roundtrip.test.ts
// END_MODULE_MAP: M-TEST-CONTRACTS-TODAY-FIXTURE-ROUNDTRIP

import { describe, expect, it } from "vitest"
import fs from "node:fs"
import path from "node:path"
import rawDayPayloadV2 from "@/e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json"
import { dayPayloadV2 } from "@/e2e/mock-visual/fixtures/day-v2-2026-07-08"
import { TodayPayloadWireSchema } from "@/packages/contracts/runtime"
import { adaptTodayPayload } from "@/lib/adapters/today-payload"
import { TODAY } from "@/lib/today"

describe("today v2 fixture roundtrip and single source", () => {
  // START_BLOCK: FIXTURE_ROUNDTRIP
  it("proves raw JSON passes TodayPayloadWireSchema and matches wrapper", () => {
    // 1. raw JSON passes TodayPayloadWireSchema
    const parsed = TodayPayloadWireSchema.parse(rawDayPayloadV2)
    expect(parsed).toBeDefined()

    // 2. wrapper dayPayloadV2 is equal to generated parsed JSON result
    expect(dayPayloadV2).toEqual(parsed)
  })

  it("verifies V2 activation IDs, timing map and verdicts are preserved", () => {
    const v2 = dayPayloadV2.v2
    expect(v2).toBeDefined()
    if (!v2) throw new Error("v2 block is missing")

    // 3. activation IDs are preserved
    const evidenceIds = v2.activationEvidence.map((e) => e.id)
    expect(evidenceIds).toContain("act-moon-opp-pluto")
    expect(evidenceIds).toContain("act-pluto-trine-saturn")

    // 4. timing map is preserved
    const timingMap = Object.fromEntries(
      v2.activationEvidence.map((e) => [
        e.id,
        { activeFrom: e.activeFrom, exactAt: e.exactAt, activeUntil: e.activeUntil }
      ])
    )
    expect(timingMap["act-moon-opp-pluto"].activeFrom).toBe("2026-07-07T21:00:00Z")
    expect(timingMap["act-pluto-trine-saturn"].exactAt).toBe("2026-07-10T11:32:00Z")

    // 5. concrete advice verdict map is preserved
    const adviceVerdicts = Object.fromEntries(
      dayPayloadV2.concreteAdvice.rows.map((r) => [r.key, r.verdict])
    )
    expect(adviceVerdicts["work"]).toBe("caution")
    expect(adviceVerdicts["shopping"]).toBe("avoid")
  })

  it("ensures every referenced V2 activation ID exists in the evidence set", () => {
    const v2 = dayPayloadV2.v2
    expect(v2).toBeDefined()
    if (!v2) throw new Error("v2 block is missing")

    const evidenceIds = new Set(v2.activationEvidence.map((e) => e.id))

    // 6. every referenced activation ID exists in evidence set
    // Check topActivatedTargets
    for (const target of v2.activationSummary.topActivatedTargets) {
      for (const id of target.activationIds) {
        expect(evidenceIds.has(id)).toBe(true)
      }
    }

    // Check whyToday
    for (const item of v2.whyToday) {
      for (const id of item.activationIds) {
        expect(evidenceIds.has(id)).toBe(true)
      }
    }

    // Check concreteAdvice evidence references
    for (const row of dayPayloadV2.concreteAdvice.rows) {
      for (const ev of row.evidence) {
        if (ev.activationId) {
          expect(evidenceIds.has(ev.activationId)).toBe(true)
        }
      }
    }

    // Check score contributions
    for (const score of Object.values(v2.scoreBreakdown)) {
      for (const contribution of score.contributions) {
        if (contribution.source === "activation") {
          expect(evidenceIds.has(contribution.sourceId)).toBe(true)
        }
      }
    }
  })

  it("proves wrong known timing type is rejected", () => {
    // 7. wrong known timing type rejected generated Zod
    const malformed = {
      ...rawDayPayloadV2,
      v2: {
        ...rawDayPayloadV2.v2,
        activationEvidence: [
          {
            ...rawDayPayloadV2.v2.activationEvidence[0],
            activeFrom: 12345, // should be string or null
          },
        ],
      },
    }
    expect(TodayPayloadWireSchema.safeParse(malformed).success).toBe(false)
  })

  it("proves adaptTodayPayload does not copy/reparse v2 block", () => {
    // 8. adaptTodayPayload(dayPayloadV2).payload.v2 === dayPayloadV2.v2
    const { payload } = adaptTodayPayload(dayPayloadV2, TODAY)
    expect(payload.v2).toBe(dayPayloadV2.v2)
  })

  it("enforces single payload source guard on the TS wrapper file", () => {
    // 9. source guard verifies wrapper implementation details
    const wrapperPath = path.resolve(__dirname, "../../e2e/mock-visual/fixtures/day-v2-2026-07-08.ts")
    const content = fs.readFileSync(wrapperPath, "utf8")

    expect(content).toContain('import rawDayPayloadV2 from "./json/day-v2-2026-07-08.json"')
    expect(content).toContain("TodayPayloadWireSchema.parse(rawDayPayloadV2)")
    expect(content).not.toContain("Сегодня особенно заметен внутренний конфликт")
    expect(content).not.toContain("previewTiming")

    // Check that only one committed visual payload JSON source exists for this fixture
    const jsonDir = path.resolve(__dirname, "../../e2e/mock-visual/fixtures/json")
    const jsonFiles = fs.readdirSync(jsonDir).filter((file) => file.endsWith(".json"))
    const todayJsonFiles = jsonFiles.filter((file) => file.startsWith("day-v2-2026-07-08"))
    expect(todayJsonFiles).toEqual(["day-v2-2026-07-08.json"])

    // verify wrapper does not contain manual initializer dayPayloadV2 = { ... }
    const manualInitializerRegex = /dayPayloadV2[^=]*=\s*\{/
    expect(manualInitializerRegex.test(content)).toBe(false)
  })
  // END_BLOCK: FIXTURE_ROUNDTRIP
})
