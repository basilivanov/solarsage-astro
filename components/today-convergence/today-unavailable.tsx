// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_UNAVAILABLE — deterministic calculation retry state.
// ROLE: Shows a truthful unavailable calculation status without partial facts.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNAVAILABLE
// purpose: Render state=unavailable status and one retry action.
// owns:
//   - components/today-convergence/today-unavailable.tsx
// inputs: optional retry callback.
// outputs: role=alert status and public unavailable selector.
// dependencies: none.
// side_effects: invokes onRetry on explicit click.
// emitted_logs: none.
// invariants: no hero, impulse, event, or fabricated fallback is rendered here.
// failure_policy: retry is a safe no-op when no callback is supplied.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNAVAILABLE

// START_MODULE_MAP: M-TODAY-CONVERGENCE-UNAVAILABLE
// public_entrypoints:
//   - TodayUnavailable
// semantic_blocks:
//   - UNAVAILABLE_STATUS: honest status and retry button.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-UNAVAILABLE

type Props = { onRetry?: () => void };

// START_BLOCK: UNAVAILABLE_STATUS
export function TodayUnavailable({ onRetry }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNAVAILABLE.TodayUnavailable
  // purpose: Render calculation-unavailable status with a retry action.
  // inputs: onRetry — optional parent transport/recalculation callback.
  // returns: role=alert status section.
  // side_effects: invokes onRetry from the button.
  // emitted_logs: none.
  // error_behavior: no-op callback when omitted.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNAVAILABLE.TodayUnavailable
  return (
    <section data-testid="today-unavailable" role="alert" className="rounded-[24px] border border-border/60 bg-card p-5">
      <p className="font-serif text-[22px] leading-tight">Не удалось рассчитать день. Обновить</p>
      <button
        type="button"
        onClick={() => onRetry?.()}
        className="mt-4 min-h-11 rounded-full border border-border/70 bg-background px-5 text-[13px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        Обновить
      </button>
    </section>
  );
}
// END_BLOCK: UNAVAILABLE_STATUS
