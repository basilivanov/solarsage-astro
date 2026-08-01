// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_MAIN_EVENT — quiet-day exceptional event block.
// ROLE: Renders deterministic main-event identity, summary, polarity, timezone-aware EventTime, and drilldown.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-MAIN-EVENT
// purpose: Render a quiet-day main event without merging it into convergence content.
// owns:
//   - components/today-convergence/main-event.tsx
// inputs: generated TodayConvergenceMainEvent, optional published snapshot id, and payload timezone.
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
  snapshotId?: string | null;
  timezone?: string | null;
};

// START_BLOCK: MAIN_EVENT
export function MainEvent({ event, snapshotId, timezone }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  // purpose: Render the deterministic main event block.
  // inputs: event — generated main event payload; snapshotId — published snapshot identity for drilldown; timezone — payload timezone for absolute event time.
  // returns: accessible main-event article.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: generated event fields are rendered as received.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-MAIN-EVENT.MainEvent
  const href = snapshotId
    ? `/day/snapshots/${encodeURIComponent(snapshotId)}/spheres/${event.sphere}`
    : null;
  const content = (
    <>
      <p className="text-[13px] font-medium uppercase leading-[18px] tracking-[0.14em] text-muted-foreground">
        Главное событие дня
      </p>
      <h2 className="mt-2 font-serif text-[20px] leading-[26px]">{getTodaySphereLabel(event.sphere)}</h2>
      <p
        className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[13px] leading-[18px] ${getPolarityToneClasses(event.polarity)}`}
      >
        {getPolarityLabel(event.polarity)}
      </p>
      <time className="mt-3 block text-[15px] leading-[22px] tabular-nums" dateTime={getEventTimeDateTime(event.time)}>
        {formatEventTime(event.time, timezone)}
      </time>
      {event.summary ? (
        <p className="mt-2 text-[15px] leading-[22px] text-pretty text-foreground/85">{event.summary.text}</p>
      ) : null}
    </>
  );

  return (
    <article
      data-testid="main-event"
      data-polarity={event.polarity}
      data-has-summary={event.summary ? "true" : "false"}
      className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm"
    >
      {href ? (
        <a
          href={href}
          className="block rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
        >
          {content}
        </a>
      ) : content}
    </article>
  );
}
// END_BLOCK: MAIN_EVENT
