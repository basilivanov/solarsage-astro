
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_NATAL
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/natal.ts
// owns:
//   - packages/contracts/natal.ts
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
// Source of truth is apps/api/app/schemas/natal.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type { NatalPayload as _NatalPayload } from "./index";

export type NatalPayload = _NatalPayload;
export type NatalSection = _NatalPayload["sections"][number];

// Tolerant union retained for legacy block renderers. Pydantic models four
// known kinds; unknown kinds are gracefully skipped per LA-FRONT-GRACEFUL-SKIP.
// Legacy code uses this as a structural type at the call site only.
export type NatalBlock =
  | { type: "paragraph"; text: string }
  | { type: "bullets"; items: string[] }
  | {
      type: "highlights";
      items: { id: string; title: string; text: string; tone?: string }[];
    }
  | { type: "quote"; text: string; source?: string }
  | { type: string; [k: string]: unknown };
