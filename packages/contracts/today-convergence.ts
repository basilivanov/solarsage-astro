// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY_CONVERGENCE — generated P1-F contract shim.
// ROLE: Exposes Today Convergence types and Zod schemas without local wire definitions.
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-CONVERGENCE
// purpose: Provide the feature import surface for generated Today Convergence contracts.
// owns:
//   - packages/contracts/today-convergence.ts
// inputs: generated OpenAPI TypeScript and Zod artifacts.
// outputs: feature-prefixed type aliases and generated runtime schema re-exports.
// dependencies: ./_generated, ./_generated.zod.
// side_effects: none.
// emitted_logs: none.
// invariants: no local interfaces, unions, objects, or handwritten Zod definitions.
// failure_policy: compile failure when generated names drift.
// END_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-CONVERGENCE

// START_MODULE_MAP: M-WEB-CONTRACTS-TODAY-CONVERGENCE
// public_entrypoints:
//   - TodayConvergencePayload
//   - TodayConvergencePayloadWireSchema
//   - feature-prefixed nested type and schema aliases
// semantic_blocks:
//   - GENERATED_TYPE_ALIASES: aliases into components from ./_generated.
//   - GENERATED_ZOD_EXPORTS: direct re-exports from ./_generated.zod.
// owned_tests:
//   - __tests__/contracts/today-convergence-contract.test.ts
// END_MODULE_MAP: M-WEB-CONTRACTS-TODAY-CONVERGENCE

import type { components } from "./_generated";

// START_BLOCK: GENERATED_TYPE_ALIASES
export type TodayConvergenceBirthCapabilities = components["schemas"]["TodayConvergenceBirthCapabilities"];
export type TodayConvergenceBirthTime = components["schemas"]["TodayConvergenceBirthTime"];
export type TodayConvergenceNarrativeClaim = components["schemas"]["TodayConvergenceNarrativeClaim"];
export type TodayConvergenceSummary = components["schemas"]["TodayConvergenceSummary"];
export type TodayConvergenceGroup = components["schemas"]["TodayConvergenceGroup"];
export type TodayConvergenceEventTime = components["schemas"]["TodayConvergenceEventTime"];
export type TodayConvergenceEvent = components["schemas"]["TodayConvergenceEvent"];
export type TodayConvergenceImpulse = components["schemas"]["TodayConvergenceImpulse"];
export type TodayConvergenceLookahead = components["schemas"]["TodayConvergenceLookahead"];
export type TodayConvergenceMainEvent = components["schemas"]["TodayConvergenceMainEvent"];
export type TodayConvergencePeriodContext = components["schemas"]["TodayConvergencePeriodContext"];
export type TodayConvergencePreviewTeaser = components["schemas"]["TodayConvergencePreviewTeaser"];
export type TodayConvergencePayload = components["schemas"]["TodayConvergencePayload"];
// END_BLOCK: GENERATED_TYPE_ALIASES

// START_BLOCK: GENERATED_ZOD_EXPORTS
export {
  TodayConvergenceBirthCapabilities as TodayConvergenceBirthCapabilitiesWireSchema,
  TodayConvergenceBirthTime as TodayConvergenceBirthTimeWireSchema,
  TodayConvergenceNarrativeClaim as TodayConvergenceNarrativeClaimWireSchema,
  TodayConvergenceSummary as TodayConvergenceSummaryWireSchema,
  TodayConvergenceGroup as TodayConvergenceGroupWireSchema,
  TodayConvergenceEventTime as TodayConvergenceEventTimeWireSchema,
  TodayConvergenceEvent as TodayConvergenceEventWireSchema,
  TodayConvergenceImpulse as TodayConvergenceImpulseWireSchema,
  TodayConvergenceLookahead as TodayConvergenceLookaheadWireSchema,
  TodayConvergenceMainEvent as TodayConvergenceMainEventWireSchema,
  TodayConvergencePeriodContext as TodayConvergencePeriodContextWireSchema,
  TodayConvergencePreviewTeaser as TodayConvergencePreviewTeaserWireSchema,
  TodayConvergencePayload as TodayConvergencePayloadWireSchema,
} from "./_generated.zod";
// END_BLOCK: GENERATED_ZOD_EXPORTS
