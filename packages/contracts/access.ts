
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_ACCESS
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/access.ts
// owns:
//   - packages/contracts/access.ts
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
// Source of truth is apps/api/app/schemas/access.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type { AccessSummary as _AccessSummary } from "./index";

export type AccessSummary = _AccessSummary;
export type UserAccessState = _AccessSummary["user"];
