
// ############################################################################
// AI_HEADER: MODULE_CONTRACTS_TODAY
// ROLE: Contract schema
// DEPENDENCIES: local modules
// GRACE_ANCHORS: []
// SLICE: SLICE-CONTRACTS
// ############################################################################

// START_MODULE_CONTRACT
// purpose: Contract schema — packages/contracts/today.ts
// owns:
//   - packages/contracts/today.ts
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
// Source of truth is apps/api/app/schemas/today.py (Pydantic).
// New code MUST import from "@/packages/contracts" (barrel) which
// re-exports the openapi-typescript output in ./_generated.
//
// This file is kept ONLY because legacy/frontend/** still imports from
// "./today" by relative path. legacy/** is inert (INV-LEGACY-INERT) and
// will be removed/rewritten by PHASE-2-FRONTEND-PORT (W-2.0…W-2.8).
// When the last legacy import is gone, this file is deleted.

import type {
  TodayPayload as _TodayPayload,
  ContentAccessState as _ContentAccessState,
} from "./index";

export type TodayPayload = _TodayPayload;
export type ContentAccessState = _ContentAccessState;

// Narrow string-union helpers retained for legacy callers. They are
// structural subsets of the generated types; if Pydantic widens these,
// drift gate (W-1.1B) catches it.
export type DayStatus = "supportive" | "steady" | "tense";
export type WhyParagraph = { kind: "paragraph"; text: string };
export type WhyBullets = { kind: "bullets"; items: string[] };
export type WhyBlock = WhyParagraph | WhyBullets;
export type WhySection = {
  id: string;
  title: string;
  iconName?: string;
  blocks: WhyBlock[];
};
export type WeekStripDay = {
  date: string;
  dayStatus: DayStatus;
  isToday: boolean;
};
export type MicrocopyItem = {
  id: string;
  textShort: string;
  textLong: string;
  tone: ("bold" | "supportive" | "gentle" | "warning")[];
  scope: "today" | "morning" | "evening";
};
export type YesterdayEcho = {
  hadCheckin: boolean;
  mood?: 1 | 2 | 3 | 4 | 5;
  accuracy?: 1 | 2 | 3 | 4 | 5;
  closureText: string;
  transition: "released" | "intensified" | "shifted" | "continued";
};
export type TopFlag = {
  iconName: string;
  title: string;
  summary: string;
  hint?: { whyToday?: string; howItFeels?: string };
};
