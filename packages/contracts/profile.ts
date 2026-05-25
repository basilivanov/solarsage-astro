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
