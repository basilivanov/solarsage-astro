// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_GENERAL_SKY — non-personal Today context marker.
// ROLE: Clearly labels general-background forecasts without LLM interpretation.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-GENERAL-SKY
// purpose: Render the required non-personal forecast marker for personal=false.
// owns:
//   - components/today-convergence/day-general-sky.tsx
// inputs: no dynamic narrative input.
// outputs: data-testid=day-general-sky with deterministic explanatory copy.
// dependencies: none.
// side_effects: none.
// emitted_logs: none.
// invariants: never renders an LLM claim or implies exact personal timing.
// failure_policy: caller omits the component when personal is not false.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-GENERAL-SKY

// START_MODULE_MAP: M-TODAY-CONVERGENCE-GENERAL-SKY
// public_entrypoints:
//   - DayGeneralSky
// semantic_blocks:
//   - GENERAL_SKY: explicit non-personal forecast marker.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-GENERAL-SKY

// START_BLOCK: GENERAL_SKY
export function DayGeneralSky() {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-GENERAL-SKY.DayGeneralSky
  // purpose: Show that the deterministic sky is general rather than personal.
  // inputs: none.
  // returns: accessible general-sky aside.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: none; caller controls whether it is rendered.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-GENERAL-SKY.DayGeneralSky
  return (
    <aside data-testid="day-general-sky" className="rounded-2xl border border-border/60 bg-card/60 px-4 py-3">
      <p className="font-medium">Общий фон дня</p>
      <p className="mt-1 text-[13px] leading-5 text-muted-foreground">Не персональный прогноз: точное время рождения неизвестно.</p>
    </aside>
  );
}
// END_BLOCK: GENERAL_SKY
