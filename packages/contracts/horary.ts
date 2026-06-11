
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_HORARY
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// #########################################// START_MODULE_CONTRACT
// purpose: Contract: horary
// owns:
//   - packages/contracts/horary.ts
// inputs: n/a (types)
// outputs: n/a (types)
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
