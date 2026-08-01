// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_IMPULSES — quiet-day impulse list.
// ROLE: Renders 0–3 impulse rows with generated EventTime, bound summary, and drilldown links.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES
// purpose: Render the selected quiet-day impulses and their public time/polarity attributes.
// owns:
//   - components/today-convergence/impulses-list.tsx
// inputs: generated TodayConvergenceImpulse array and optional published snapshot id.
// outputs: data-testid=impulses-list and data-testid=impulse-{eventId} rows.
// dependencies: today-formatters, packages/contracts/today-convergence.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: no list is rendered for an empty array; summary text is rendered only when supplied.
// failure_policy: caller omits the component for zero impulses.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES

// START_MODULE_MAP: M-TODAY-CONVERGENCE-IMPULSES
// public_entrypoints:
//   - ImpulsesList
// semantic_blocks:
//   - IMPULSES: capped quiet-day rows and time mode contract.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-IMPULSES

import type { TodayConvergenceImpulse } from "@/packages/contracts/today-convergence";
import {
  formatEventTime,
  getPolarityLabel,
  getPolarityToneClasses,
  getTodaySphereLabel,
} from "./today-formatters";

type Props = {
  impulses: readonly TodayConvergenceImpulse[];
  snapshotId?: string | null;
};

// START_BLOCK: IMPULSES
export function ImpulsesList({ impulses, snapshotId }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  // purpose: Render the quiet-day impulse list.
  // inputs: impulses — generated selected impulse rows; snapshotId — published snapshot identity for drilldown links.
  // returns: list DOM or null when the array is empty.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: empty input renders no block, preserving the quiet period context.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  if (impulses.length === 0) return null;

  return (
    <section data-testid="impulses-list" data-count={String(impulses.length)} className="space-y-3">
      <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Импульсы дня
      </h2>
      <ul className="space-y-2">
        {impulses.map((impulse) => {
          const href = snapshotId
            ? `/day/snapshots/${encodeURIComponent(snapshotId)}/spheres/${impulse.sphere}`
            : null;
          const rowAttributes = {
            "data-testid": `impulse-${impulse.eventId}`,
            "data-polarity": impulse.polarity,
            "data-time-mode": impulse.time.mode,
            "data-has-summary": impulse.summary ? "true" : "false",
          } as const;
          const rowContent = (
            <>
              <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1 text-[15px] leading-[22px]">
                <time className="tabular-nums" dateTime={impulse.time.peak ?? undefined}>
                  {formatEventTime(impulse.time)}
                </time>
                <span className="font-medium">{getTodaySphereLabel(impulse.sphere)}</span>
              </div>
              <p
                className={`mt-1 inline-flex rounded-full px-2 py-0.5 text-[13px] leading-[18px] ${getPolarityToneClasses(impulse.polarity)}`}
              >
                {getPolarityLabel(impulse.polarity)}
              </p>
              {impulse.summary ? (
                <p className="mt-2 text-[15px] leading-[22px] text-pretty text-foreground/85">
                  {impulse.summary.text}
                </p>
              ) : null}
            </>
          );

          return href ? (
            <li key={impulse.eventId} className="list-none">
              <a
                {...rowAttributes}
                href={href}
                className="block rounded-2xl border border-border/60 bg-card p-4 shadow-sm transition-colors hover:border-border focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
              >
                {rowContent}
              </a>
            </li>
          ) : (
            <li
              key={impulse.eventId}
              {...rowAttributes}
              className="rounded-2xl border border-border/60 bg-card p-4"
            >
              {rowContent}
            </li>
          );
        })}
      </ul>
    </section>
  );
}
// END_BLOCK: IMPULSES
