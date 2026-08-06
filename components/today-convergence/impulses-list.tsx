// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_IMPULSES — grouped quiet-day impulse list.
// ROLE: Renders one understandable sphere block per group and opens a human-first drilldown sheet.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES
// purpose: Group selected quiet-day impulses by sphere, resolve event titles from the Today ledger, and expose each card as a dialog trigger.
// owns:
//   - components/today-convergence/impulses-list.tsx
// inputs: generated TodayConvergenceImpulse array, TodayConvergenceEvent ledger, timezone, and parent-owned drilldown callback.
// outputs: grouped sphere cards with exact event titles, data-testid=impulses-list, data-testid=impulse-{eventId} facts, impulse-event-meta-{eventId} and impulse-event-time-{eventId} selectors, and drilldown triggers.
// dependencies: today-formatters, packages/contracts/today-convergence.ts.
// side_effects: delegates the selected sphere to the parent sheet host.
// emitted_logs: none.
// invariants: no list is rendered for an empty array; every original impulse keeps its public test and semantic attributes.
// failure_policy: caller omits the component for zero impulses.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES

// START_MODULE_MAP: M-TODAY-CONVERGENCE-IMPULSES
// public_entrypoints:
//   - ImpulsesList
// semantic_blocks:
//   - IMPULSES: capped quiet-day rows, event-ledger title lookup, responsive title/time/polarity meta, and time mode contract.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-IMPULSES

import { ChevronRight } from "lucide-react";
import type {
  TodayConvergenceEvent,
  TodayConvergenceImpulse,
} from "@/packages/contracts/today-convergence";
import {
  formatEventTime,
  getEventTimeDateTime,
  getPolarityLabel,
  getPolarityToneClasses,
  getTodaySphereLabel,
} from "./today-formatters";
import type { ImpulseDrilldownGroup } from "./impulse-drilldown-sheet";

type Props = {
  impulses: readonly TodayConvergenceImpulse[];
  events?: readonly TodayConvergenceEvent[];
  timezone?: string | null;
  onOpenDrilldown: (sphere: TodayConvergenceImpulse["sphere"]) => void;
};

function groupImpulses(
  impulses: readonly TodayConvergenceImpulse[],
  events: readonly TodayConvergenceEvent[],
): ImpulseDrilldownGroup[] {
  const eventById = new Map(events.map((event) => [event.id, event] as const));
  const groups = new Map<TodayConvergenceImpulse["sphere"], TodayConvergenceImpulse[]>();
  for (const impulse of impulses) {
    const group = groups.get(impulse.sphere);
    if (group) group.push(impulse);
    else groups.set(impulse.sphere, [impulse]);
  }
  return Array.from(groups, ([sphere, groupedImpulses]) => ({
    sphere,
    impulses: groupedImpulses,
    events: groupedImpulses.flatMap((impulse) => {
      const event = eventById.get(impulse.eventId);
      return event ? [event] : [];
    }),
  }));
}

// START_BLOCK: IMPULSES
export function ImpulsesList({ impulses, events = [], timezone, onOpenDrilldown }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  // purpose: Render the quiet-day impulse list.
  // inputs: impulses — generated selected impulse rows; events — matching Today event ledger; timezone — display context; onOpenDrilldown — parent sheet action.
  // returns: grouped list DOM or null when the array is empty.
  // side_effects: delegates the selected sphere to the parent sheet host.
  // emitted_logs: none.
  // error_behavior: empty input renders no block, preserving the quiet period context.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  if (impulses.length === 0) return null;

  const eventById = new Map(events.map((event) => [event.id, event] as const));
  const groups = groupImpulses(impulses, events);

  return (
    <section data-testid="impulses-list" data-count={String(impulses.length)} data-group-count={String(groups.length)} className="space-y-3">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
        Импульсы дня
      </h2>
      <div className="space-y-3">
        {groups.map((group) => (
          <article
            key={group.sphere}
            data-testid={`impulse-group-${group.sphere}`}
            data-sphere={group.sphere}
            data-impulse-count={String(group.impulses.length)}
            className="rounded-[24px] border border-border/40 bg-card p-5 shadow-(--shadow-card)"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-serif text-[17px] leading-[22px] text-foreground">{getTodaySphereLabel(group.sphere)}</h3>
                <p className="mt-1 text-[13px] leading-[18px] text-muted-foreground">
                  {group.impulses.length === 1 ? "Один сигнал сегодня" : `${group.impulses.length} сигнала сегодня`}
                </p>
              </div>
              <span aria-hidden className="mt-1 h-2 w-2 flex-none rounded-full bg-foreground/70" />
            </div>

            <ul className="mt-4 space-y-2">
              {group.impulses.map((impulse) => {
                const eventTitle = eventById.get(impulse.eventId)?.title;
                const cardClassName = "relative block w-full rounded-[20px] border border-border/40 bg-card p-4 pr-10 text-left shadow-(--shadow-card) transition-[border-color,box-shadow] duration-150 hover:border-primary/30 hover:shadow-(--shadow-lift) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none";
                const cardContent = (
                  <>
                    <div
                      data-testid={`impulse-event-meta-${impulse.eventId}`}
                      className="flex min-w-0 flex-col gap-1 text-[15px] leading-[22px] xl:flex-row xl:items-baseline xl:justify-between xl:gap-x-4"
                    >
                      {eventTitle ? (
                        <h4
                          data-testid={`impulse-event-title-${impulse.eventId}`}
                          className="min-w-0 break-words font-serif text-[17px] leading-[22px] text-foreground xl:flex-none xl:whitespace-nowrap"
                        >
                          {eventTitle}
                        </h4>
                      ) : null}
                      <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1 xl:flex-none xl:flex-nowrap xl:whitespace-nowrap">
                        <time
                          data-testid={`impulse-event-time-${impulse.eventId}`}
                          className="min-w-0 break-words text-[13px] tabular-nums text-muted-foreground xl:whitespace-nowrap"
                          dateTime={getEventTimeDateTime(impulse.time)}
                        >
                          {formatEventTime(impulse.time, timezone)}
                        </time>
                        <span className={`rounded-full px-2 py-0.5 text-[13px] leading-[18px] ${getPolarityToneClasses(impulse.polarity)}`}>
                          {getPolarityLabel(impulse.polarity)}
                        </span>
                      </div>
                    </div>
                    {impulse.summary ? (
                      <p className="mt-2 text-[15px] leading-[23px] text-pretty text-foreground/90">
                        {impulse.summary.text}
                      </p>
                    ) : null}
                    <ChevronRight
                      aria-hidden
                      className="absolute right-3 top-4 h-4 w-4 text-muted-foreground/50"
                    />
                  </>
                );
                return (
                  <li
                    key={impulse.eventId}
                    data-testid={`impulse-${impulse.eventId}`}
                    data-polarity={impulse.polarity}
                    data-time-mode={impulse.time.mode}
                    data-has-summary={impulse.summary ? "true" : "false"}
                    data-has-event-title={eventTitle ? "true" : "false"}
                    className="min-w-0"
                  >
                    <button
                      type="button"
                      aria-haspopup="dialog"
                      aria-label={`Открыть разбор сферы «${getTodaySphereLabel(impulse.sphere)}»`}
                      onClick={() => onOpenDrilldown(group.sphere)}
                      className={cardClassName}
                    >
                      {cardContent}
                    </button>
                  </li>
                );
              })}
            </ul>

          </article>
        ))}
      </div>
    </section>
  );
}
// END_BLOCK: IMPULSES
