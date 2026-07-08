// ############################################################################
// AI_HEADER: MODULE_LIB_LUNAR_PRESENTATION
// ROLE: Presentation-only lunar glyph and label helpers for backend facts.
// ############################################################################

// START_MODULE_CONTRACT: M-LIB-LUNAR-PRESENTATION
// purpose: Map backend lunar phase fields to UI glyphs and display labels.
// owns:
//   - lib/lunar-presentation.ts
// inputs:
//   - backend phaseIndex/phaseLabel values from CalendarLunarFields
// outputs:
//   - emoji glyphs and fallback labels for rendering only
// dependencies:
//   - none
// side_effects: none
// emitted_logs: none
// invariants:
//   - does not compute lunar/astrological facts from dates.
// failure_policy:
//   - returns fallback glyph/label for unknown/null fields.
// END_MODULE_CONTRACT: M-LIB-LUNAR-PRESENTATION

// START_MODULE_MAP: M-LIB-LUNAR-PRESENTATION
// public_entrypoints:
//   - lunarPhaseGlyph
//   - lunarPhaseLabel
// semantic_blocks:
//   - PHASE_PRESENTATION: backend-value to glyph/label mapping
// owned_tests:
//   - __tests__/components/CalendarScreen.test.tsx
// END_MODULE_MAP: M-LIB-LUNAR-PRESENTATION

import type { CalendarDayReadModel } from "@/lib/contracts/calendar"

const PHASE_GLYPHS = ["🌑", "🌒", "🌓", "🌔", "🌕", "🌖", "🌗", "🌘"] as const
const PHASE_LABELS = [
  "новолуние",
  "раст. серп",
  "перв. четв.",
  "раст. Луна",
  "полнолуние",
  "убыв. Луна",
  "посл. четв.",
  "убыв. серп",
] as const

type LunarFields = CalendarDayReadModel["lunar"]

// START_BLOCK: PHASE_PRESENTATION
export function lunarPhaseGlyph(lunar: LunarFields | null | undefined): string {
  // START_FUNCTION_CONTRACT: F-M-LIB-LUNAR-PRESENTATION.lunarPhaseGlyph
  // purpose: Return a display glyph for a backend lunar phase index.
  // inputs: lunar — backend lunar fields, possibly null/partial.
  // returns: string — emoji glyph for UI presentation.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back to crescent glyph for unknown indexes.
  // END_FUNCTION_CONTRACT: F-M-LIB-LUNAR-PRESENTATION.lunarPhaseGlyph
  const index = lunar?.phaseIndex
  return typeof index === "number" && index >= 0 && index < PHASE_GLYPHS.length
    ? PHASE_GLYPHS[index]
    : "☾"
}

export function lunarPhaseLabel(lunar: LunarFields | null | undefined): string | null {
  // START_FUNCTION_CONTRACT: F-M-LIB-LUNAR-PRESENTATION.lunarPhaseLabel
  // purpose: Return a display label for backend lunar fields.
  // inputs: lunar — backend lunar fields, possibly null/partial.
  // returns: string | null — localized label when available.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: falls back from backend label to phaseIndex label to phase key.
  // END_FUNCTION_CONTRACT: F-M-LIB-LUNAR-PRESENTATION.lunarPhaseLabel
  if (lunar?.phaseLabel) return lunar.phaseLabel
  const index = lunar?.phaseIndex
  if (typeof index === "number" && index >= 0 && index < PHASE_LABELS.length) {
    return PHASE_LABELS[index]
  }
  return lunar?.phase ?? null
}
// END_BLOCK: PHASE_PRESENTATION
