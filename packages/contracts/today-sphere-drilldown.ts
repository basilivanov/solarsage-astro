// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY-SPHERE-DRILLDOWN — generated sphere evidence shim.
// ROLE: Exposes deterministic Today sphere drilldown types and schemas.
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-SPHERE-DRILLDOWN
// purpose: Provide the feature import surface for generated sphere drilldown contracts.
// owns:
//   - packages/contracts/today-sphere-drilldown.ts
// inputs: generated OpenAPI TypeScript and Zod artifacts.
// outputs: feature-prefixed type aliases and generated runtime schema exports.
// dependencies: ./_generated, ./_generated.zod.
// side_effects: none.
// emitted_logs: none.
// invariants: no local wire shapes or handwritten validators.
// failure_policy: compile failure when generated names drift.
// END_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-SPHERE-DRILLDOWN

// START_MODULE_MAP: M-WEB-CONTRACTS-TODAY-SPHERE-DRILLDOWN
// public_entrypoints:
//   - TodaySphereDrilldownPayload
//   - TodaySphereDrilldownConvergence
//   - TodaySphereDrilldownPayloadWireSchema
// semantic_blocks:
//   - GENERATED_TYPE_ALIASES: aliases into generated OpenAPI components.
//   - GENERATED_ZOD_EXPORTS: direct aliases from generated Zod schemas.
// owned_tests:
//   - none
// END_MODULE_MAP: M-WEB-CONTRACTS-TODAY-SPHERE-DRILLDOWN

import type { components } from "./_generated";

export type TodaySphereDrilldownConvergence = components["schemas"]["TodaySphereDrilldownConvergence"];
export type TodaySphereDrilldownPayload = components["schemas"]["TodaySphereDrilldownPayload"];

export {
  TodaySphereDrilldownConvergence as TodaySphereDrilldownConvergenceWireSchema,
  TodaySphereDrilldownPayload as TodaySphereDrilldownPayloadWireSchema,
} from "./_generated.zod";
