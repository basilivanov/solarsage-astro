// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_UNIFIED — convergence day in the quiet-day list language.
// ROLE: Renders selected convergence groups as per-sphere signal cards (same visual
//       language as ImpulsesList) with an evidence badge instead of the hero slab.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNIFIED
// purpose: Present a convergence_today state as a unified per-sphere signal list: converged spheres first, each signal card carrying facet label, event title, polarity, summary, and a convergence evidence badge.
// owns:
//   - components/today-convergence/convergence-unified-list.tsx
// inputs: generated convergence groups, Today event ledger, targetDate, timezone, contentState, drilldown callback, retry callback.
// outputs: data-testid=convergence-unified-list DOM with per-signal selectors; pending/unavailable states delegated to TodayNarrative.
// dependencies: today-formatters, facet-labels, today-narrative, impulse-drilldown-sheet types, packages/contracts.
// side_effects: delegates sphere drilldown and retry to parents.
// emitted_logs: none.
// invariants: every selected group renders exactly one signal card under its sphere; facet=null shows the sphere label only; no flat claim dump.
// failure_policy: empty group list renders nothing.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-UNIFIED

// START_MODULE_MAP: M-TODAY-CONVERGENCE-UNIFIED
// public_entrypoints:
//   - ConvergenceUnifiedList
// semantic_blocks:
//   - UNIFIED_LIST: per-sphere grouping, evidence badge, signal cards.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-UNIFIED

import { ChevronRight } from "lucide-react";
import type {
  TodayConvergenceEvent,
  TodayConvergenceGroup,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import { getFacetLabel, readSignalFacet } from "@/lib/display/facet-labels";
import {
  formatEventTime,
  formatTargetDateRu,
  getEventTimeDateTime,
  getPolarityLabel,
  getPolarityToneClasses,
  getTodaySphereLabel,
} from "./today-formatters";
import { TodayNarrative } from "./today-narrative";

type Props = {
  groups: readonly TodayConvergenceGroup[];
  events: readonly TodayConvergenceEvent[];
  targetDate: TodayConvergencePayload["targetDate"];
  timezone: TodayConvergencePayload["timezone"];
  contentState: TodayConvergencePayload["contentState"];
  onOpenDrilldown: (sphere: string) => void;
  onRetry?: () => void;
};

function evidenceLabel(level: TodayConvergenceGroup["evidenceLevel"]): string {
  return level === "high" ? "высокая" : "средняя";
}

// START_BLOCK: UNIFIED_LIST
export function ConvergenceUnifiedList({
  groups,
  events,
  targetDate,
  timezone,
  contentState,
  onOpenDrilldown,
  onRetry,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNIFIED.ConvergenceUnifiedList
  // purpose: Render convergence groups as quiet-day-style sphere sections with signal cards.
  // inputs: groups — selected convergence groups; events — fact ledger for titles/times; targetDate/timezone — display context; contentState — LLM zone state; onOpenDrilldown/onRetry — parent callbacks.
  // returns: unified list DOM or null for an empty group list.
  // side_effects: delegates drilldown navigation and retry.
  // emitted_logs: none.
  // error_behavior: empty groups produce no block; non-ready contentState still surfaces via TodayNarrative.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-UNIFIED
  if (groups.length === 0) return null;

  const eventById = new Map(events.map((event) => [event.id, event] as const));
  const bySphere = new Map<string, TodayConvergenceGroup[]>();
  for (const group of groups) {
    const bucket = bySphere.get(group.sphere);
    if (bucket) bucket.push(group);
    else bySphere.set(group.sphere, [group]);
  }
  const sphereGroups = Array.from(bySphere, ([sphere, sphereSignals]) => ({
    sphere,
    signals: sphereSignals,
  })).sort((a, b) => b.signals.length - a.signals.length);
  const targetDateLabel = formatTargetDateRu(targetDate);
  const strongestEvidence = groups.some((group) => group.evidenceLevel === "high") ? "high" : groups[0].evidenceLevel;

  return (
    <section
      data-testid="convergence-unified-list"
      data-group-count={String(groups.length)}
      className="space-y-3"
    >
      <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-1">
        <h2 className="text-[11px] font-medium uppercase tracking-[0.18em] text-muted-foreground/80">
          Что сошлось {targetDateLabel}
        </h2>
        <span
          data-testid="convergence-evidence-badge"
          data-evidence-level={strongestEvidence}
          className="inline-flex items-center gap-2 text-[12px] leading-[18px] text-muted-foreground/80"
        >
          <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-primary/60" />
          Доказательность: {evidenceLabel(strongestEvidence)}
        </span>
      </div>

      <div className="space-y-3">
        {sphereGroups.map(({ sphere, signals }) => (
          <article
            key={sphere}
            data-testid={`unified-group-${sphere}`}
            data-sphere={sphere}
            data-signal-count={String(signals.length)}
            className="rounded-[24px] border border-border/40 bg-card p-5 shadow-(--shadow-card)"
          >
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-serif text-[17px] leading-[22px] text-foreground">{getTodaySphereLabel(sphere)}</h3>
                <p className="mt-1 text-[13px] leading-[18px] text-muted-foreground">
                  {signals.length === 1 ? "Один сигнал сегодня" : `${signals.length} сигнала сегодня`}
                </p>
              </div>
              <span aria-hidden className="mt-1 h-2 w-2 flex-none rounded-full bg-foreground/70" />
            </div>

            <ul className="mt-4 space-y-2">
              {signals.map((group) => {
                const facet = readSignalFacet(group);
                const facetLabel = getFacetLabel(facet);
                const event = group.eventIds.map((id) => eventById.get(id)).find((e) => e != null);
                return (
                  <li
                    key={group.id}
                    data-testid={`unified-signal-${group.id}`}
                    data-polarity={group.polarity}
                    data-facet={facet ?? undefined}
                    data-evidence-level={group.evidenceLevel}
                    className="min-w-0"
                  >
                    <button
                      type="button"
                      aria-haspopup="dialog"
                      aria-label={`Открыть разбор сферы «${getTodaySphereLabel(sphere)}»`}
                      onClick={() => onOpenDrilldown(sphere)}
                      className="relative block w-full rounded-[20px] border border-border/40 bg-card p-4 pr-10 text-left shadow-(--shadow-card) transition-[border-color,box-shadow] duration-150 hover:border-primary/30 hover:shadow-(--shadow-lift) focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none"
                    >
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-[13px] font-medium leading-[18px] text-foreground">
                          {facetLabel ?? getTodaySphereLabel(sphere)}
                        </span>
                        <span className={`rounded-full px-2 py-0.5 text-[12px] leading-[18px] ${getPolarityToneClasses(group.polarity)}`}>
                          {getPolarityLabel(group.polarity)}
                        </span>
                      </div>
                      {event ? (
                        <div className="mt-1.5 flex min-w-0 flex-col gap-1 xl:flex-row xl:items-baseline xl:justify-between xl:gap-x-4">
                          <h4 className="min-w-0 break-words font-serif text-[17px] leading-[22px] text-foreground xl:flex-none">
                            {event.title}
                          </h4>
                          <time
                            className="min-w-0 break-words text-[13px] tabular-nums text-muted-foreground xl:flex-none xl:whitespace-nowrap"
                            dateTime={getEventTimeDateTime(event.time)}
                          >
                            {formatEventTime(event.time, timezone)}
                          </time>
                        </div>
                      ) : null}
                      {group.summary ? (
                        <p className="mt-2 text-[15px] leading-[23px] text-pretty text-foreground/90">
                          {group.summary.text}
                        </p>
                      ) : null}
                      <ChevronRight aria-hidden className="absolute right-3 top-4 h-4 w-4 text-muted-foreground/50" />
                    </button>
                  </li>
                );
              })}
            </ul>
          </article>
        ))}
      </div>

      {contentState !== "ready" ? (
        <TodayNarrative state={contentState} claims={[]} onRetry={onRetry} />
      ) : null}
    </section>
  );
}
// END_BLOCK: UNIFIED_LIST
