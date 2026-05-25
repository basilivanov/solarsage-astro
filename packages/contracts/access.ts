// @deprecated since W-1.1B. Do NOT add or modify shapes here.
// Source of truth is apps/api/app/schemas/access.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel).

import type { AccessSummary as _AccessSummary } from "./index";

export type AccessSummary = _AccessSummary;
export type UserAccessState = _AccessSummary["user"];
