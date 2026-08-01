// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_IMPULSES — quiet-day impulse list.
// ROLE: Renders 0–3 deterministic impulse rows with generated EventTime formatting.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-IMPULSES
// purpose: Render the selected quiet-day impulses and their public time/polarity attributes.
// owns:
//   - components/today-convergence/impulses-list.tsx
// inputs: generated TodayConvergenceImpulse array.
// outputs: data-testid=impulses-list and data-testid=impulse-{eventId} rows.
// dependencies: today-formatters, packages/contracts/today-convergence.ts.
// side_effects: none.
// emitted_logs: none.
// invariants: no list is rendered for an empty array; no LLM fields are read here.
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

type Props = { impulses: readonly TodayConvergenceImpulse[] };

// START_BLOCK: IMPULSES
export function ImpulsesList({ impulses }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-IMPULSES.ImpulsesList
  // purpose: Render the quiet-day impulse list.
  // inputs: impulses — generated selected impulse rows.
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
        {impulses.map((impulse) => (
          <li
            key={impulse.eventId}
            data-testid={`impulse-${impulse.eventId}`}
            data-polarity={impulse.polarity}
            data-time-mode={impulse.time.mode}
            className="rounded-2xl border border-border/60 bg-card p-4"
          >
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
          </li>
        ))}
      </ul>
    </section>
  );
}
// END_BLOCK: IMPULSES
