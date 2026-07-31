// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY-SPHERE-PAGE — generated sphere page shim.
// ROLE: Exposes generated static sphere page types and schemas.
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-SPHERE-PAGE
// purpose: Provide the feature import surface for generated sphere page contracts.
// owns:
//   - packages/contracts/today-sphere-page.ts
// inputs: generated OpenAPI TypeScript and Zod artifacts.
// outputs: feature-prefixed type aliases and generated runtime schema exports.
// dependencies: ./_generated, ./_generated.zod.
// side_effects: none.
// emitted_logs: none.
// invariants: no local wire shapes or handwritten validators.
// failure_policy: compile failure when generated names drift.
// END_MODULE_CONTRACT: M-WEB-CONTRACTS-TODAY-SPHERE-PAGE

// START_MODULE_MAP: M-WEB-CONTRACTS-TODAY-SPHERE-PAGE
// public_entrypoints:
//   - TodaySpherePagePayload
//   - TodaySphereNatal
//   - TodaySphereNatalParagraph
//   - TodaySpherePeriodItem
//   - TodaySpherePagePayloadWireSchema
// semantic_blocks:
//   - GENERATED_TYPE_ALIASES: aliases into generated OpenAPI components.
//   - GENERATED_ZOD_EXPORTS: direct aliases from generated Zod schemas.
// owned_tests:
//   - none
// END_MODULE_MAP: M-WEB-CONTRACTS-TODAY-SPHERE-PAGE

import type { components } from "./_generated";

export type TodaySphereNatal = components["schemas"]["TodaySphereNatal"];
export type TodaySphereNatalParagraph = components["schemas"]["TodaySphereNatalParagraph"];
export type TodaySpherePeriodItem = components["schemas"]["TodaySpherePeriodItem"];
export type TodaySpherePagePayload = components["schemas"]["TodaySpherePagePayload"];

export {
  TodaySphereNatal as TodaySphereNatalWireSchema,
  TodaySphereNatalParagraph as TodaySphereNatalParagraphWireSchema,
  TodaySpherePeriodItem as TodaySpherePeriodItemWireSchema,
  TodaySpherePagePayload as TodaySpherePagePayloadWireSchema,
} from "./_generated.zod";
