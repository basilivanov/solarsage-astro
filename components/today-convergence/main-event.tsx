// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_MAIN_EVENT — quiet-day exceptional event block.
// ROLE: Renders deterministic main-event identity, polarity, and EventTime.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-MAIN-EVENT
// purpose: Render a quiet-day main event without merging it into convergence content.
// owns:
//   - components/today-convergence/main-event.tsx
// inputs: generated TodayConvergenceMainEvent.
// outputs: data-testid=main-event block with public polarity and time attributes.
// dependencies: today-formatters, packages/contracts/today-convergence.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: main event is deterministic; it never uses convergence-only copy.
// failure_policy: caller omits the component when mainEvent is null.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-MAIN-EVENT

// START_MODULE_MAP: M-TODAY-CONVERGENCE-MAIN-EVENT
// public_entrypoints:
//   - MainEvent
// semantic_blocks:
//   - MAIN_EVENT: title, sphere, polarity, and time.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-MAIN-EVENT

import type { TodayConvergenceMainEvent } from "@/packages/contracts/today-convergence";
import { formatEventTime, getPolarityLabel, getTodaySphereLabel } from "./today-formatters";

type Props = { event: TodayConvergenceMainEvent };

// START_BLOCK: MAIN_EVENT
export function MainEvent({ event }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  // purpose: Render the deterministic main event block.
  // inputs: event — generated main event payload.
  // returns: accessible main-event article.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated event fields are rendered as received.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  return (
    <article
      data-testid="main-event"
      data-polarity={event.polarity}
      className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm"
    >
      <p className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Главное событие дня
      </p>
      <h2 className="mt-2 font-serif text-[20px] leading-tight">{getTodaySphereLabel(event.sphere)}</h2>
      <p className="mt-1 text-[13px] text-muted-foreground">{getPolarityLabel(event.polarity)}</p>
      <time className="mt-3 block text-[15px] tabular-nums" dateTime={event.time.peak ?? undefined}>
        {formatEventTime(event.time)}
      </time>
    </article>
  );
}
// END_BLOCK: MAIN_EVENT
