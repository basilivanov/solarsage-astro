// ############################################################################
// AI_HEADER: MODULE_PERIOD_TECHNIQUE_COPY — deterministic explanations for long-lived period techniques.
// ROLE: Keeps technical technique names visible while adding concise, bounded human-first context.
// ############################################################################

// START_MODULE_CONTRACT: M-PERIOD-TECHNIQUE-COPY
// purpose: Resolve one supported period technique to static explanations for sphere and Today drilldown views.
// owns:
//   - components/today-convergence/period-technique-copy.ts
// inputs: period technique enum from the generated sphere payload, including unknown runtime values.
// outputs: stable label and three short explanatory copy blocks.
// dependencies: none; the registry is local and deterministic.
// side_effects: none.
// emitted_logs: none.
// invariants: all four wire techniques have entries; unknown or future values use a neutral fallback.
// failure_policy: never throws for absent or unsupported technique values.
// END_MODULE_CONTRACT: M-PERIOD-TECHNIQUE-COPY

// START_MODULE_MAP: M-PERIOD-TECHNIQUE-COPY
// public_entrypoints:
//   - PERIOD_TECHNIQUE_KEYS
//   - PERIOD_TECHNIQUE_COPY
//   - PERIOD_TECHNIQUE_FALLBACK
//   - getPeriodTechniqueCopy
// semantic_blocks:
//   - TECHNIQUE_REGISTRY: exhaustive static explanations for supported period techniques.
//   - FALLBACK: neutral copy for absent or future enum values.
// owned_tests:
//   - __tests__/components/today-convergence/sphere-page.test.tsx
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-PERIOD-TECHNIQUE-COPY

// START_BLOCK: TECHNIQUE_REGISTRY
export const PERIOD_TECHNIQUE_KEYS = [
  "annual_profection",
  "solar_return",
  "firdar_major",
  "firdar_minor",
] as const;

export type PeriodTechniqueKey = (typeof PERIOD_TECHNIQUE_KEYS)[number];

export type PeriodTechniqueCopy = Readonly<{
  label: string;
  whatItIs: string;
  howItAffectsNow: string;
  whatYouMayNotice: string;
}>;

export const PERIOD_TECHNIQUE_COPY: Readonly<Record<PeriodTechniqueKey, PeriodTechniqueCopy>> = {
  annual_profection: {
    label: "Профекция",
    whatItIs: "Годовой цикл, который выделяет одну тему и сферу жизни.",
    howItAffectsNow: "Он задаёт фон года: эта тема чаще возвращается в решения и задачи.",
    whatYouMayNotice: "Можно заметить повторяющиеся вопросы, обязанности или поводы уделить этой сфере внимание.",
  },
  solar_return: {
    label: "Соляр",
    whatItIs: "Годовой цикл от одного дня рождения до следующего.",
    howItAffectsNow: "Он задаёт общий сюжет личного года и подсвечивает сферу, которой сейчас нужно больше внимания.",
    whatYouMayNotice: "Можно заметить, что события года чаще собираются вокруг одной темы или направления.",
  },
  firdar_major: {
    label: "Большой фирдар",
    whatItIs: "Длинный период последовательности планетарных тем.",
    howItAffectsNow: "Он задаёт устойчивый фон этапа и окрашивает то, что длится дольше одного события.",
    whatYouMayNotice: "Можно заметить повторяющийся ритм нагрузки, интереса или ответственности в этой сфере.",
  },
  firdar_minor: {
    label: "Малый фирдар",
    whatItIs: "Более короткий подпериод внутри большого фирдара.",
    howItAffectsNow: "Он уточняет текущий акцент и показывает, какая тема выходит вперёд сейчас.",
    whatYouMayNotice: "Можно заметить более конкретные поводы, разговоры или задачи внутри общего периода.",
  },
};
// END_BLOCK: TECHNIQUE_REGISTRY

export const PERIOD_TECHNIQUE_FALLBACK: PeriodTechniqueCopy = {
  label: "Периодическая техника",
  whatItIs: "Один из длительных способов описать фон периода.",
  howItAffectsNow: "Сейчас она помогает обозначить тему, которая остаётся в поле внимания.",
  whatYouMayNotice: "Можно замечать повторяющиеся обстоятельства вокруг этой темы.",
};

// START_BLOCK: FALLBACK
export function getPeriodTechniqueCopy(
  technique: string | null | undefined,
): PeriodTechniqueCopy {
  // START_FUNCTION_CONTRACT: F-M-PERIOD-TECHNIQUE-COPY.getPeriodTechniqueCopy
  // purpose: Resolve supported technique copy without trusting runtime enum completeness.
  // inputs: technique — generated technique key or an absent/future runtime value.
  // returns: the matching static explanation or a neutral fallback.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: never throws; unsupported values return PERIOD_TECHNIQUE_FALLBACK.
  // END_FUNCTION_CONTRACT: F-M-PERIOD-TECHNIQUE-COPY.getPeriodTechniqueCopy
  if (technique && Object.prototype.hasOwnProperty.call(PERIOD_TECHNIQUE_COPY, technique)) {
    return PERIOD_TECHNIQUE_COPY[technique as PeriodTechniqueKey];
  }
  return PERIOD_TECHNIQUE_FALLBACK;
}
// END_BLOCK: FALLBACK
