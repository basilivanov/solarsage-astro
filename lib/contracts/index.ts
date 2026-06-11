
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_INDEX
// ROLE: Library module
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Library module — lib/contracts/index.ts
// owns:
//   - lib/contracts/index.ts
// inputs: varies
// outputs: varies
// dependencies: local modules
// side_effects: varies
// emitted_logs: n/a
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT

// START_MODULE_MAP
// mapping:
//   - export: default
//     contract: main export
// END_MODULE_MAP

/**
 * Централизованный экспорт всех контрактов.
 *
 * Импортируйте отсюда для удобства:
 *   import { validateAccessInfo, AccessInfo } from "@/lib/contracts"
 */

export * from "./access"
export * from "./profile"
export * from "./city"
export * from "./calendar"
export * from "./chat"
export * from "./natal"
