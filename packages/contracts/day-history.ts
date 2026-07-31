// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_DAY_HISTORY — generated Today history contract shim.
// ROLE: Exposes DayHistory types through the generated contracts barrel.
// ############################################################################

// START_MODULE_CONTRACT: M-WEB-CONTRACTS-DAY-HISTORY
// purpose: Provide the feature import surface for published Today history types.
// owns:
//   - packages/contracts/day-history.ts
// inputs: generated OpenAPI aliases from packages/contracts/index.ts.
// outputs: DayHistoryPayload and DayHistoryItem type aliases.
// dependencies: ./index.
// side_effects: none.
// emitted_logs: none.
// invariants: no local wire shape declarations; generated contracts remain source of truth.
// failure_policy: compile failure when generated names drift.
// END_MODULE_CONTRACT: M-WEB-CONTRACTS-DAY-HISTORY

// START_MODULE_MAP: M-WEB-CONTRACTS-DAY-HISTORY
// public_entrypoints:
//   - DayHistoryPayload
//   - DayHistoryItem
// semantic_blocks:
//   - GENERATED_TYPE_ALIASES: aliases into the generated contract barrel.
// owned_tests:
//   - none
// END_MODULE_MAP: M-WEB-CONTRACTS-DAY-HISTORY

import type { DayHistoryItem as _DayHistoryItem, DayHistoryPayload as _DayHistoryPayload } from "./index";

export type DayHistoryItem = _DayHistoryItem;
export type DayHistoryPayload = _DayHistoryPayload;
