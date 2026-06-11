
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_INDEX
// ROLE: Lib — index.ts
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-UNMAPPED
// #########################################// START_MODULE_CONTRACT
// purpose: Library: index
// owns:
//   - lib/contracts/index.ts
// inputs: Function arguments
// outputs: Return values
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
