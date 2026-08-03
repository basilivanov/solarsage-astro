// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SPHERE_NAVIGATOR — canonical sphere navigation.
// ROLE: Renders the fixed twelve-sphere navigator with explicit text summaries for active Today spheres.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR
// purpose: Render the fixed canonical sphere order with public Today signal summaries and real sphere paths.
// owns:
//   - components/today-convergence/sphere-navigator.tsx
// inputs: generated TodayConvergencePayload.
// outputs: nav, 12 tile selectors, visible active summaries, snapshot drilldown links for marked tiles, and static sphere links otherwise.
// dependencies: lib/display/sphere-labels, packages/contracts/today-convergence.ts.
// side_effects: browser navigation through ordinary links only.
// emitted_logs: none.
// invariants: order is canonical; active state is conveyed by text as well as a neutral supplementary dot; inactive tiles have no Today summary.
// failure_policy: absent selected blocks mean all markers are false.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR

// START_MODULE_MAP: M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR
// public_entrypoints:
//   - SphereNavigator
// semantic_blocks:
//   - NAVIGATOR: twelve fixed canonical sphere tiles.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR

import { CANONICAL_PRODUCT_ORDER } from "@/lib/display/sphere-labels";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";
import { SphereIcon } from "./sphere-icons";

type Props = {
  payload: TodayConvergencePayload;
  rail?: boolean;
};

type SphereTodaySummary = {
  count: number;
  hasSupportive: boolean;
  hasTense: boolean;
  hasMixed: boolean;
};

function addTodayFact(
  summaries: Map<string, SphereTodaySummary>,
  sphere: string,
  polarity: "supportive" | "tense" | "mixed",
) {
  const current = summaries.get(sphere) ?? {
    count: 0,
    hasSupportive: false,
    hasTense: false,
    hasMixed: false,
  };
  current.count += 1;
  if (polarity === "supportive") current.hasSupportive = true;
  if (polarity === "tense") current.hasTense = true;
  if (polarity === "mixed") current.hasMixed = true;
  summaries.set(sphere, current);
}

function todaySphereSummaries(payload: TodayConvergencePayload): Map<string, SphereTodaySummary> {
  const summaries = new Map<string, SphereTodaySummary>();
  for (const event of payload.events) {
    addTodayFact(summaries, event.sphere, event.polarity);
  }

  // Older fixture-shaped callers can still provide the selected cards without
  // the flat events array. Keep active labels honest without treating period
  // or lookahead context as a fact from today.
  if (payload.events.length === 0) {
    if (payload.mainEvent) addTodayFact(summaries, payload.mainEvent.sphere, payload.mainEvent.polarity);
    for (const impulse of payload.impulses) addTodayFact(summaries, impulse.sphere, impulse.polarity);
  }
  return summaries;
}

function signalCountLabel(count: number): string {
  const mod10 = count % 10;
  const mod100 = count % 100;
  const word = mod10 === 1 && mod100 !== 11
    ? "сигнал"
    : mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)
      ? "сигнала"
      : "сигналов";
  return `${count} ${word}`;
}

function activeSummary(summary: SphereTodaySummary | undefined): string | null {
  if (!summary) return null;
  const polarities = [
    summary.hasSupportive ? "поддержка" : null,
    summary.hasTense ? "напряжение" : null,
    summary.hasMixed ? "смешанно" : null,
  ].filter((label): label is string => label !== null);
  return `${signalCountLabel(summary.count)}${polarities.length > 0 ? ` · ${polarities.join(" + ")}` : ""}`;
}

// START_BLOCK: NAVIGATOR
export function SphereNavigator({ payload, rail = false }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR.SphereNavigator
  // purpose: Render all twelve canonical sphere links and visible summaries for spheres with Today facts.
  // inputs: payload — generated Today Convergence envelope.
  // returns: accessible sphere navigation.
  // side_effects: ordinary link navigation only.
  // emitted_logs: none.
  // error_behavior: absent Today facts render twelve unmarked tiles; period/lookahead context alone never marks a sphere.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR.SphereNavigator
  const summaries = todaySphereSummaries(payload);

  return (
    <nav data-testid="sphere-navigator" aria-label="Сферы жизни" className="space-y-3">
      <h2 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
        Сферы жизни
      </h2>
      <ul
        className={`grid min-w-0 grid-cols-3 gap-2 sm:grid-cols-4 ${
          rail ? "lg:grid-cols-3" : "lg:grid-cols-6"
        }`}
      >
        {CANONICAL_PRODUCT_ORDER.map((sphere) => {
          const summary = summaries.get(sphere.key);
          const todaySummary = activeSummary(summary);
          const hasToday = Boolean(summary);
          return (
            <li key={sphere.key}>
              <a
                href={
                  hasToday && payload.snapshotId
                    ? `/day/snapshots/${encodeURIComponent(payload.snapshotId)}/spheres/${sphere.key}`
                    : `/day/spheres/${sphere.key}`
                }
                data-testid={`sphere-tile-${sphere.key}`}
                data-has-today={String(hasToday)}
                data-today-count={summary ? String(summary.count) : "0"}
                data-today-summary={todaySummary ?? undefined}
                aria-label={todaySummary ? `${sphere.label}: ${todaySummary}` : sphere.label}
                className="relative flex h-full min-h-[88px] min-w-0 w-full flex-col items-center justify-center gap-1.5 rounded-2xl border border-border/40 bg-card px-1.5 py-2 text-center text-[12.5px] font-medium leading-4 text-foreground transition-[border-color,box-shadow,transform] duration-150 hover:-translate-y-0.5 hover:border-primary/30 hover:shadow-(--shadow-lift) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transform-none motion-reduce:transition-none"
              >
                <SphereIcon sphere={sphere.key} className="h-6 w-6 shrink-0 text-foreground/75" />
                <span className="max-w-full whitespace-nowrap text-[12.5px] font-medium">{sphere.label}</span>
                {todaySummary ? (
                  <span
                    data-testid={`sphere-tile-summary-${sphere.key}`}
                    className="max-w-full text-[11px] leading-4 text-muted-foreground"
                  >
                    {todaySummary}
                  </span>
                ) : null}
                <span
                  aria-hidden
                  className="absolute right-2 top-2 h-2 w-2 rounded-full bg-foreground"
                  style={{ opacity: hasToday ? 1 : 0 }}
                />
              </a>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
// END_BLOCK: NAVIGATOR
