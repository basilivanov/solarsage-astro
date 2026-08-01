// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_IMPULSES — grouped quiet-day impulse list.
// ROLE: Renders one understandable sphere block per group and opens a human-first drilldown sheet.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES
// purpose: Group selected quiet-day impulses by sphere, resolve event titles from the Today ledger, and render a modal CTA.
// owns:
//   - components/today-convergence/impulses-list.tsx
// inputs: generated TodayConvergenceImpulse array, TodayConvergenceEvent ledger, optional snapshot/date/timezone context.
// outputs: grouped sphere cards with exact event titles, data-testid=impulses-list, data-testid=impulse-{eventId} facts, impulse-event-meta-{eventId} and impulse-event-time-{eventId} selectors, and drilldown triggers.
// dependencies: today-formatters, impulse-drilldown-sheet, packages/contracts/today-convergence.ts.
// side_effects: opens the child sheet; the child lazily fetches sphere context.
// emitted_logs: delegated ui.fetch_started, ui.fetch_succeeded, ui.fetch_failed from the child sheet.
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

import { useState } from "react";
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
import {
  ImpulseDrilldownSheet,
  type ImpulseDrilldownGroup,
} from "./impulse-drilldown-sheet";

type Props = {
  impulses: readonly TodayConvergenceImpulse[];
  events?: readonly TodayConvergenceEvent[];
  snapshotId?: string | null;
  targetDate?: string | null;
  timezone?: string | null;
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
export function ImpulsesList({ impulses, events = [], snapshotId, targetDate, timezone }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  // purpose: Render the quiet-day impulse list.
  // inputs: impulses — generated selected impulse rows; events — matching Today event ledger; snapshotId/targetDate/timezone — modal context.
  // returns: grouped list DOM or null when the array is empty.
  // side_effects: opens the selected sphere sheet; lazy network work is delegated to the sheet.
  // emitted_logs: none.
  // error_behavior: empty input renders no block, preserving the quiet period context.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  const [openSphere, setOpenSphere] = useState<TodayConvergenceImpulse["sphere"] | null>(null);
  if (impulses.length === 0) return null;

  const eventById = new Map(events.map((event) => [event.id, event] as const));
  const groups = groupImpulses(impulses, events);
  const activeGroup = openSphere ? groups.find((group) => group.sphere === openSphere) : undefined;

  return (
    <section data-testid="impulses-list" data-count={String(impulses.length)} data-group-count={String(groups.length)} className="space-y-3">
      <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Импульсы дня
      </h2>
      <div className="space-y-3">
        {groups.map((group) => (
          <article
            key={group.sphere}
            data-testid={`impulse-group-${group.sphere}`}
            data-sphere={group.sphere}
            data-impulse-count={String(group.impulses.length)}
            className="rounded-2xl border border-border/60 bg-card p-4 shadow-sm"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-serif text-[20px] leading-[26px]">{getTodaySphereLabel(group.sphere)}</h3>
                <p className="mt-1 text-[13px] leading-[18px] text-muted-foreground">
                  {group.impulses.length === 1 ? "Один сигнал сегодня" : `${group.impulses.length} сигнала сегодня`}
                </p>
              </div>
              <span aria-hidden className="mt-1 h-2 w-2 flex-none rounded-full bg-foreground/70" />
            </div>

            <ul className="mt-4 space-y-2">
              {group.impulses.map((impulse) => {
                const eventTitle = eventById.get(impulse.eventId)?.title;
                return (
                  <li
                    key={impulse.eventId}
                    data-testid={`impulse-${impulse.eventId}`}
                    data-polarity={impulse.polarity}
                    data-time-mode={impulse.time.mode}
                    data-has-summary={impulse.summary ? "true" : "false"}
                    data-has-event-title={eventTitle ? "true" : "false"}
                    className="min-w-0 rounded-xl border border-border/50 bg-background/60 p-3"
                  >
                    <div
                      data-testid={`impulse-event-meta-${impulse.eventId}`}
                      className="flex min-w-0 flex-col gap-1 text-[15px] leading-[22px] xl:flex-row xl:items-baseline xl:justify-between xl:gap-x-4"
                    >
                      {eventTitle ? (
                        <h4
                          data-testid={`impulse-event-title-${impulse.eventId}`}
                          className="min-w-0 break-words text-[16px] font-medium leading-[22px] text-foreground xl:flex-none xl:whitespace-nowrap"
                        >
                          {eventTitle}
                        </h4>
                      ) : null}
                      <div className="flex min-w-0 flex-wrap items-baseline gap-x-2 gap-y-1 xl:flex-none xl:flex-nowrap xl:whitespace-nowrap">
                        <time
                          data-testid={`impulse-event-time-${impulse.eventId}`}
                          className="min-w-0 break-words tabular-nums xl:whitespace-nowrap"
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
                      <p className="mt-2 text-[15px] leading-[22px] text-pretty text-foreground/85">
                        {impulse.summary.text}
                      </p>
                    ) : null}
                  </li>
                );
              })}
            </ul>

            <button
              type="button"
              data-testid={`impulse-drilldown-trigger-${group.sphere}`}
              aria-haspopup="dialog"
              onClick={() => setOpenSphere(group.sphere)}
              className="mt-4 inline-flex min-h-11 w-full items-center justify-center rounded-full border border-foreground/80 px-4 py-2 text-[13px] font-medium transition hover:bg-muted/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
            >
              Разобрать, как это может проявиться
            </button>
          </article>
        ))}
      </div>

      {activeGroup ? (
        <ImpulseDrilldownSheet
          group={activeGroup}
          snapshotId={snapshotId}
          targetDate={targetDate}
          timezone={timezone}
          onClose={() => setOpenSphere(null)}
        />
      ) : null}
    </section>
  );
}
// END_BLOCK: IMPULSES
