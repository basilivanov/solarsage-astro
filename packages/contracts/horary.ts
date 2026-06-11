
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_HORARY
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/horary.ts
// owns:
//   - packages/contracts/horary.ts
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

import type {
  HoraryQuestionCreate as _HoraryQuestionCreate,
  HoraryQuestionRead as _HoraryQuestionRead,
  HoraryAnswerRead as _HoraryAnswerRead,
  HoraryQuotaRead as _HoraryQuotaRead,
} from "./index";

export type HoraryQuestionCreate = _HoraryQuestionCreate;
export type HoraryQuestionRead = _HoraryQuestionRead;
export type HoraryAnswerRead = _HoraryAnswerRead;
export type HoraryQuotaRead = _HoraryQuotaRead;
