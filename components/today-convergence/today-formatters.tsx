// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_FORMATTERS — deterministic presentation helpers for Today.
// ROLE: Formats generated wire values into approved Russian labels without inventing payload fields.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-FORMATTERS
// purpose: Convert canonical sphere, polarity, and EventTime values into stable UI strings.
// owns:
//   - components/today-convergence/today-formatters.tsx
// inputs: generated Today Convergence nested wire values.
// outputs: Russian labels and time strings used by Today components.
// dependencies: packages/contracts/today-convergence.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: exact clocks appear only for EventTime.mode=exact; no LLM or legacy fields are read.
// failure_policy: use a deterministic neutral label for incomplete optional time fields.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-FORMATTERS

// START_MODULE_MAP: M-TODAY-CONVERGENCE-FORMATTERS
// public_entrypoints:
//   - getTodaySphereLabel
//   - getPolarityLabel
//   - formatEventTime
// semantic_blocks:
//   - CANONICAL_LABELS: product sphere and polarity labels.
//   - EVENT_TIME: exact, partofday, and date presentation.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-FORMATTERS

import type {
  TodayConvergenceEventTime,
  TodayConvergenceGroup,
} from "@/packages/contracts/today-convergence";

const SPHERE_LABELS: Record<TodayConvergenceGroup["primarySphere"], string> = {
  work: "Работа",
  money: "Деньги",
  documents: "Документы",
  relationships: "Отношения",
  sport: "Спорт",
  communication: "Общение",
  health: "Здоровье",
  decisions: "Решения",
  travel: "Поездки",
  creativity: "Творчество",
  study: "Учёба",
  shopping: "Покупки",
};

const POLARITY_LABELS: Record<"supportive" | "tense" | "mixed", string> = {
  supportive: "поддержка",
  tense: "напряжение",
  mixed: "смешанно",
};

const PART_OF_DAY_LABELS: Record<"night" | "morning" | "day" | "evening", string> = {
  night: "ночью",
  morning: "утром",
  day: "днём",
  evening: "вечером",
};

// START_BLOCK: CANONICAL_LABELS
export function getTodaySphereLabel(key: TodayConvergenceGroup["primarySphere"]): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getTodaySphereLabel
  // purpose: Return the approved human-readable label for a canonical sphere key.
  // inputs: key — generated canonical Today sphere key.
  // returns: stable Russian sphere label.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated union typing prevents unknown keys at call sites.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getTodaySphereLabel
  return SPHERE_LABELS[key];
}

export function getPolarityLabel(polarity: "supportive" | "tense" | "mixed"): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getPolarityLabel
  // purpose: Provide text that carries polarity meaning independently of color.
  // inputs: polarity — generated convergence polarity.
  // returns: Russian polarity label.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated union typing prevents unsupported values.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getPolarityLabel
  return POLARITY_LABELS[polarity];
}
// END_BLOCK: CANONICAL_LABELS

// START_BLOCK: EVENT_TIME
export function formatEventTime(time: TodayConvergenceEventTime): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatEventTime
  // purpose: Render EventTime according to exact, bucket, or unknown-time rules.
  // inputs: time — generated EventTime object.
  // returns: Russian time phrase without fabricated clocks.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: incomplete exact windows degrade to the available exact value.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatEventTime
  if (time.mode === "exact") {
    const window = time.start && time.end ? `, окно ${time.start}–${time.end}` : "";
    if (time.peak) return `пик ${time.peak}${window}`;
    if (window) return window.slice(2);
    return "точное время события";
  }

  if (time.mode === "partofday") {
    return time.partOfDay ? PART_OF_DAY_LABELS[time.partOfDay] : "в течение дня";
  }

  return "в течение даты";
}
// END_BLOCK: EVENT_TIME
