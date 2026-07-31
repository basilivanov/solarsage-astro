// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_LOOKAHEAD — published next-day hint.
// ROLE: Renders the optional quiet-day lookahead without calculating tomorrow.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-LOOKAHEAD
// purpose: Present the already-published next local day snapshot reference.
// owns:
//   - components/today-convergence/today-lookahead.tsx
// inputs: generated TodayConvergenceLookahead.
// outputs: data-testid=today-lookahead with target-date attribute.
// dependencies: today-formatters, packages/contracts/today-convergence.ts.
// side_effects: none; no calculation or network call.
// emitted_logs: none.
// invariants: rendered only when caller has a published lookahead object.
// failure_policy: caller omits null lookahead.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-LOOKAHEAD

// START_MODULE_MAP: M-TODAY-CONVERGENCE-LOOKAHEAD
// public_entrypoints:
//   - TodayLookahead
// semantic_blocks:
//   - LOOKAHEAD: target date and sphere label.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-LOOKAHEAD

import type { TodayConvergenceLookahead } from "@/packages/contracts/today-convergence";
import { getTodaySphereLabel } from "./today-formatters";

type Props = { lookahead: TodayConvergenceLookahead };

// START_BLOCK: LOOKAHEAD
export function TodayLookahead({ lookahead }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-LOOKAHEAD.TodayLookahead
  // purpose: Render the optional next-day sphere hint.
  // inputs: lookahead — generated published lookahead object.
  // returns: accessible lookahead aside.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated targetDate and sphere are shown without fallback calculation.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-LOOKAHEAD.TodayLookahead
  return (
    <aside
      data-testid="today-lookahead"
      data-target-date={lookahead.targetDate}
      className="rounded-2xl border border-border/60 bg-card/70 px-4 py-3 text-[14px]"
    >
      Завтра факторы сходятся в сфере «{getTodaySphereLabel(lookahead.sphere)}».
    </aside>
  );
}
// END_BLOCK: LOOKAHEAD
