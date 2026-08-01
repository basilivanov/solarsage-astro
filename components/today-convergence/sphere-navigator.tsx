// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_SPHERE_NAVIGATOR — canonical sphere navigation.
// ROLE: Renders the fixed twelve-sphere navigator and neutral today markers.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR
// purpose: Render the fixed canonical sphere order with public today markers and real sphere paths.
// owns:
//   - components/today-convergence/sphere-navigator.tsx
// inputs: generated TodayConvergencePayload.
// outputs: nav, 12 tile selectors, snapshot drilldown links for marked tiles, and static sphere links otherwise.
// dependencies: lib/display/sphere-labels, packages/contracts/today-convergence.ts.
// side_effects: browser navigation through ordinary links only.
// emitted_logs: none.
// invariants: order is canonical; markers are neutral and never tone-colored.
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

function selectedSpheres(payload: TodayConvergencePayload): Set<string> {
  const result = new Set<string>();
  for (const group of payload.convergences) {
    result.add(group.primarySphere);
    if (group.secondarySphere) result.add(group.secondarySphere);
  }
  if (payload.mainEvent) result.add(payload.mainEvent.sphere);
  for (const impulse of payload.impulses) result.add(impulse.sphere);
  if (payload.periodContext?.sphere) result.add(payload.periodContext.sphere);
  for (const sphere of payload.previewTeaser?.spheres ?? []) result.add(sphere);
  return result;
}

// START_BLOCK: NAVIGATOR
export function SphereNavigator({ payload, rail = false }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR.SphereNavigator
  // purpose: Render all twelve canonical sphere links and selected-sphere markers.
  // inputs: payload — generated Today Convergence envelope.
  // returns: accessible sphere navigation.
  // side_effects: ordinary link navigation only.
  // emitted_logs: none.
  // error_behavior: empty payload selections render twelve unmarked tiles.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-SPHERE-NAVIGATOR.SphereNavigator
  const spheres = selectedSpheres(payload);

  return (
    <nav data-testid="sphere-navigator" aria-label="Сферы жизни" className="space-y-3">
      <h2 className="text-[12px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
        Сферы жизни
      </h2>
      <ul
        className={`grid min-w-0 grid-cols-3 gap-2 sm:grid-cols-4 ${
          rail ? "lg:grid-cols-3" : "lg:grid-cols-6"
        }`}
      >
        {CANONICAL_PRODUCT_ORDER.map((sphere) => {
          const hasToday = spheres.has(sphere.key);
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
                aria-label={sphere.label}
                className="relative flex h-[88px] min-w-0 w-full flex-col items-center justify-center gap-1.5 rounded-2xl border border-border/60 bg-card/60 px-1.5 text-center text-[13px] leading-4 text-foreground transition hover:border-primary/50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
              >
                <SphereIcon sphere={sphere.key} className="h-6 w-6 shrink-0" />
                <span className="max-w-full whitespace-nowrap">{sphere.label}</span>
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
