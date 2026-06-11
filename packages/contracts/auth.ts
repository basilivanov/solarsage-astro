
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_AUTH
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/auth.ts
// owns:
//   - packages/contracts/auth.ts
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
// Source of truth is apps/api/app/schemas/auth.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type {
  AuthError as _AuthError,
  AuthSession as _AuthSession,
  TelegramAuthRequest as _TelegramAuthRequest,
} from "./index";

export type TelegramAuthRequest = _TelegramAuthRequest;
export type AuthSession = _AuthSession;
export type AuthError = _AuthError;
