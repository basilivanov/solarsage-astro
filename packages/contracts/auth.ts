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
