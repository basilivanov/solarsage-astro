
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_PROFILE
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/profile.ts
// owns:
//   - packages/contracts/profile.ts
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

// @deprecated since W-1.1B. Do NOT add or modify shapes here.
// Source of truth is apps/api/app/schemas/profile.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type {
  BirthData as _BirthData,
  ProfileRead as _ProfileRead,
  ProfileWrite as _ProfileWrite,
} from "./index";

export type BirthData = _BirthData;
export type ProfileRead = _ProfileRead;
export type ProfileWrite = _ProfileWrite;
