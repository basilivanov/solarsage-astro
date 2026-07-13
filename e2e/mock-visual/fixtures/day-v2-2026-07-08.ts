// ############################################################################
// AI_HEADER: MODULE_E2E_MOCK_VISUAL_FIXTURE_DAY_V2_2026_07_08 — thin wrapper for JSON visual fixture.
// ROLE: Loads and validates the canonical day-v2-2026-07-08.json fixture.
// DEPENDENCIES: packages/contracts, packages/contracts/runtime, json file
// ############################################################################

// START_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2
// purpose: Synthetic V2 day fixture for mock-visual preview and Playwright.
// owns:
//   - e2e/mock-visual/fixtures/day-v2-2026-07-08.ts
// inputs: e2e/mock-visual/fixtures/json/day-v2-2026-07-08.json
// outputs: dayPayloadV2, minimalDayPayloadForDate
// dependencies: packages/contracts, packages/contracts/runtime
// side_effects: none
// invariants:
//   - throws on invalid contract during import module load
// failure_policy: throws error on invalid format
// END_MODULE_CONTRACT: M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2

// START_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2
// public_entrypoints:
//   - dayPayloadV2
//   - minimalDayPayloadForDate
// semantic_blocks:
//   - FIXTURE_LOAD: imports, parses, and validates the single JSON payload source.
//   - NEIGHBOUR_BUILDER: derived minimal day payload constructor.
// END_MODULE_MAP: M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2

// START_BLOCK: FIXTURE_LOAD
import rawDayPayloadV2 from "./json/day-v2-2026-07-08.json"
import type { TodayPayload } from "../../../packages/contracts"
import { TodayPayloadWireSchema } from "../../../packages/contracts/runtime"

export const dayPayloadV2: TodayPayload = TodayPayloadWireSchema.parse(rawDayPayloadV2)
// END_BLOCK: FIXTURE_LOAD

// START_BLOCK: NEIGHBOUR_BUILDER
// START_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2.minimalDayPayloadForDate
// purpose: Build a minimal compatible day body for week-strip neighbours.
// inputs: date - string date.
// returns: TodayPayload with minimal fields.
// side_effects: none.
// emitted_logs: none.
// error_behavior: none.
// END_FUNCTION_CONTRACT: F-M-E2E-MOCK-VISUAL-FIXTURE-DAY-V2.minimalDayPayloadForDate
export function minimalDayPayloadForDate(date: string): TodayPayload {
  return {
    ...dayPayloadV2,
    date,
    title: date,
    headline: "Соседний день недели",
    v2: null,
    meta: {
      ...dayPayloadV2.meta,
      payloadVersion: "today.v1",
      frontendPayloadVersion: 1,
    },
    concreteAdvice: {
      rows: dayPayloadV2.concreteAdvice.rows.map((r) => ({
        ...r,
        evidence: [],
        text: "Краткая сводка соседнего дня для навигации по неделе",
      })),
      counts: { good: 0, caution: 0, avoid: 0, neutral: 12 },
    },
    daySummary: {
      statusLabel: "Ровный день",
      statusLine: "соседний день недели",
      facts: [],
    },
  }
}
// END_BLOCK: NEIGHBOUR_BUILDER
