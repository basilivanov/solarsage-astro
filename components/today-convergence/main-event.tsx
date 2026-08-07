// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_MAIN_EVENT — quiet-day exceptional event block.
// ROLE: Renders deterministic main-event identity, summary, polarity, timezone-aware EventTime, and drilldown.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-MAIN-EVENT
// purpose: Render a quiet-day main event without merging it into convergence content.
// owns:
//   - components/today-convergence/main-event.tsx
// inputs: generated TodayConvergenceMainEvent and payload timezone.
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
//   - MAIN_EVENT: title, sphere, polarity, timezone-aware time, and drilldown.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-MAIN-EVENT

import type { TodayConvergenceMainEvent } from "@/packages/contracts/today-convergence";
import {
  formatEventTime,
  getEventTimeDateTime,
  getPolarityLabel,
  getPolarityToneClasses,
  getTodaySphereLabel,
} from "./today-formatters";

type Props = {
  event: TodayConvergenceMainEvent;
  timezone?: string | null;
  onOpenDrilldown?: (sphere: string) => void;
};

// START_BLOCK: MAIN_EVENT
export function MainEvent({ event, timezone, onOpenDrilldown }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  // purpose: Render the deterministic main event block.
  // inputs: event — generated main event payload; timezone — payload timezone for absolute event time.
  // returns: accessible main-event article.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated event fields are rendered as received.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  const content = (
    <>
      <p className="text-[11px] font-medium uppercase leading-[18px] tracking-[0.18em] text-muted-foreground/80">
        Главное событие дня
      </p>
      <h2 className="mt-2 font-serif text-[17px] leading-[22px] text-foreground">{getTodaySphereLabel(event.sphere)}</h2>
      <p
        className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[13px] leading-[18px] ${getPolarityToneClasses(event.polarity)}`}
      >
        {getPolarityLabel(event.polarity)}
      </p>
      <time className="mt-3 block text-[13px] leading-[18px] tabular-nums text-muted-foreground" dateTime={getEventTimeDateTime(event.time)}>
        {formatEventTime(event.time, timezone)}
      </time>
      {event.summary ? (
        <p className="mt-2 text-[15px] leading-[23px] text-pretty text-foreground/90">{event.summary.text}</p>
      ) : null}
    </>
  );

  return (
    <article
      data-testid="main-event"
      data-polarity={event.polarity}
      data-has-summary={event.summary ? "true" : "false"}
      className="rounded-[24px] border border-border/40 bg-card p-5 shadow-(--shadow-card)"
    >
      <button
        type="button"
        aria-haspopup="dialog"
        aria-label={`Открыть разбор сферы «${getTodaySphereLabel(event.sphere)}»`}
        onClick={() => onOpenDrilldown?.(event.sphere)}
        className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        {content}
      </button>
    </article>
  );
}
// END_BLOCK: MAIN_EVENT
