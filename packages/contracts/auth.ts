
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_AUTH
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// #########################################// START_MODULE_CONTRACT
// purpose: Contract: auth
// owns:
//   - packages/contracts/auth.ts
// inputs: n/a (types)
// outputs: n/a (types)
// dependencies: local modules
// side_effects: n/a (pure)
// emitted_logs: n/a (pure)
// invariants:
//   - n/a
// failure_policy: log and raise
// END_MODULE_CONTRACT
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
