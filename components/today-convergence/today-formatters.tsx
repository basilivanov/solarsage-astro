// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_FORMATTERS — deterministic presentation helpers for Today.
// ROLE: Formats generated wire values into approved Russian labels without inventing payload fields.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-FORMATTERS
// purpose: Convert canonical sphere, polarity, target-date, and EventTime values into stable human-first UI strings.
// owns:
//   - components/today-convergence/today-formatters.tsx
// inputs: generated Today Convergence nested wire values.
// outputs: Russian labels, target-date copy, product time strings, and semantic tone classes used by Today components.
// dependencies: packages/contracts/today-convergence.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: exact clocks appear only for EventTime.mode=exact; absolute instants are preferred when present; target dates are parsed as strings without browser timezone conversion; no LLM or legacy fields are read.
// failure_policy: use a deterministic neutral label for incomplete optional time fields.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-FORMATTERS

// START_MODULE_MAP: M-TODAY-CONVERGENCE-FORMATTERS
// public_entrypoints:
//   - getTodaySphereLabel
//   - getPolarityLabel
//   - getPolarityToneClasses
//   - getDayToneBackgroundClass
//   - formatTargetDateRu
//   - formatEventTime
//   - getEventTimeDateTime
// semantic_blocks:
//   - CANONICAL_LABELS: product sphere and polarity labels/classes.
//   - EVENT_TIME: exact, partofday, and date presentation.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-FORMATTERS

import type {
  TodayConvergenceEventTime,
  TodayConvergenceGroup,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import type { ProductSphereKey } from "@/lib/display/sphere-labels";

const SPHERE_LABELS: Record<ProductSphereKey, string> = {
  work: "Работа",
  finance: "Финансы",
  documents: "Документы",
  relationships: "Отношения",
  sport: "Спорт",
  communication: "Общение",
  health: "Здоровье",
  home_family: "Дом и семья",
  travel: "Поездки",
  creativity: "Творчество",
  study: "Учёба",
  friends_goals: "Друзья и планы",
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

type TodayPolarity = TodayConvergenceGroup["polarity"];

/**
 * The date-aware backend packet is additive. Keep the UI readable while this
 * worktree still accepts older generated contracts that only expose clocks.
 */
export type HumanFirstEventTime = TodayConvergenceEventTime & {
  peakAt?: string | null;
  startAt?: string | null;
  endAt?: string | null;
};

const MONTHS_RU_GEN = [
  "января",
  "февраля",
  "марта",
  "апреля",
  "мая",
  "июня",
  "июля",
  "августа",
  "сентября",
  "октября",
  "ноября",
  "декабря",
] as const;

// START_BLOCK: TARGET_DATE
export function formatTargetDateRu(targetDate: string): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatTargetDateRu
  // purpose: Format a canonical YYYY-MM-DD payload date as Russian day/month copy without timezone conversion.
  // inputs: targetDate — generated Today target date string.
  // returns: day and Russian genitive month, or the original value when its shape is invalid.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: malformed dates remain deterministic and unmodified.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatTargetDateRu
  const match = /^(\d{4})-(\d{2})-(\d{2})$/u.exec(targetDate);
  if (!match) return targetDate;

  const month = MONTHS_RU_GEN[Number(match[2]) - 1];
  const day = Number(match[3]);
  if (!month || day < 1 || day > 31) return targetDate;

  return `${day} ${month}`;
}
// END_BLOCK: TARGET_DATE

const POLARITY_TONE_CLASSES: Record<TodayPolarity, string> = {
  supportive: "text-(--tone-supportive-fg) bg-(--tone-supportive-bg)",
  tense: "text-(--tone-tense-fg) bg-(--tone-tense-bg)",
  mixed: "text-(--tone-mixed-fg) bg-(--tone-mixed-bg)",
};

const DAY_TONE_BACKGROUND_CLASSES: Record<NonNullable<TodayConvergencePayload["dayTone"]>, string> = {
  steady: "",
  supportive: "bg-(--tone-supportive-bg)",
  tense: "bg-(--tone-tense-bg)",
  mixed: "bg-(--tone-mixed-bg)",
};

// START_BLOCK: CANONICAL_LABELS
export function getTodaySphereLabel(key: string): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getTodaySphereLabel
  // purpose: Return the approved human-readable label for a canonical sphere key.
  // inputs: key — wire sphere key (string; generated union still lags the new 12 keys).
  // returns: stable Russian sphere label; "Другая сфера" for keys outside the new union.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: unknown keys degrade to a safe generic Russian label.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getTodaySphereLabel
  return SPHERE_LABELS[key as ProductSphereKey] ?? "Другая сфера";
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

export function getPolarityToneClasses(polarity: TodayPolarity): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getPolarityToneClasses
  // purpose: Return the semantic foreground/background classes for a polarity label.
  // inputs: polarity — generated polarity value.
  // returns: static Tailwind token classes that keep polarity visible beyond color alone.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated union typing prevents unsupported values.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getPolarityToneClasses
  return POLARITY_TONE_CLASSES[polarity];
}

export function getDayToneBackgroundClass(dayTone: TodayConvergencePayload["dayTone"]): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getDayToneBackgroundClass
  // purpose: Return the optional hero background class for the current day tone.
  // inputs: dayTone — generated day tone, or null for unavailable/locked states.
  // returns: a tone background class for non-steady tones, otherwise an empty string.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: null and steady intentionally return no tone accent.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getDayToneBackgroundClass
  return dayTone ? DAY_TONE_BACKGROUND_CLASSES[dayTone] : "";
}
// END_BLOCK: CANONICAL_LABELS

// START_BLOCK: EVENT_TIME
function absoluteTime(time: TodayConvergenceEventTime): HumanFirstEventTime {
  return time as HumanFirstEventTime;
}

function formatAbsoluteMoment(value: string | null | undefined, timezone?: string | null): string | null {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;

  // An absolute wire value already carries the calculation timezone offset.
  // Preserve that local representation when a legacy caller has no timezone
  // field, instead of silently shifting the instant to UTC or the browser zone.
  const formatWireLocal = () => {
    const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2})/u.exec(value);
    if (!match) return null;
    const month = MONTHS_RU_GEN[Number(match[2]) - 1];
    if (!month) return null;
    return `${Number(match[3])} ${month}, ${match[4]}:${match[5]}`;
  };

  if (!timezone) return formatWireLocal();

  const format = (timeZone: string) => new Intl.DateTimeFormat("ru-RU", {
    day: "numeric",
    hour: "2-digit",
    hourCycle: "h23",
    minute: "2-digit",
    month: "long",
    timeZone,
  }).formatToParts(date);

  let parts: Intl.DateTimeFormatPart[];
  try {
    parts = format(timezone);
  } catch {
    return formatWireLocal();
  }

  const values = Object.fromEntries(parts.map((part) => [part.type, part.value]));
  const day = values.day;
  const monthIndex = MONTHS_RU_GEN.findIndex((month) => month === values.month);
  const month = monthIndex >= 0 ? MONTHS_RU_GEN[monthIndex] : values.month;
  if (!day || !month || !values.hour || !values.minute) return null;
  return `${day} ${month}, ${values.hour}:${values.minute}`;
}

function formatAbsoluteWindow(
  startAt: string | null | undefined,
  endAt: string | null | undefined,
  timezone?: string | null,
): string {
  const start = formatAbsoluteMoment(startAt, timezone);
  const end = formatAbsoluteMoment(endAt, timezone);
  if (start && end) return `окно: с ${start} до ${end}`;
  if (start) return `окно: с ${start}`;
  if (end) return `окно: до ${end}`;
  return "";
}

export function getEventTimeDateTime(time: TodayConvergenceEventTime): string | undefined {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getEventTimeDateTime
  // purpose: Select an absolute event instant for a semantic HTML time attribute when one exists.
  // inputs: time — generated EventTime, optionally carrying date-aware absolute fields.
  // returns: absolute ISO datetime string, or undefined for clock-only legacy values.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns undefined when no usable time value exists.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.getEventTimeDateTime
  const value = absoluteTime(time);
  return value.peakAt ?? undefined;
}

export function formatEventTime(time: HumanFirstEventTime, timezone?: string | null): string {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatEventTime
  // purpose: Render EventTime according to exact, bucket, or unknown-time rules, preferring date-aware instants.
  // inputs: time — generated EventTime object; timezone — payload timezone for absolute instants.
  // returns: Russian time phrase without fabricated clocks.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: incomplete exact windows degrade to the available exact value.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-FORMATTERS.formatEventTime
  if (time.mode === "exact") {
    const absolute = absoluteTime(time);
    const peak = formatAbsoluteMoment(absolute.peakAt, timezone);
    const absoluteWindow = formatAbsoluteWindow(absolute.startAt, absolute.endAt, timezone);
    if (peak) return `пик ${peak}${absoluteWindow ? `, ${absoluteWindow}` : ""}`;
    if (absoluteWindow) return absoluteWindow;

    const window = time.start && time.end
      ? `, окно ${time.start}${time.start > time.end ? " → " : "–"}${time.end}`
      : "";
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
