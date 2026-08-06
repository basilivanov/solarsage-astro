// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_HERO — convergence_today hero block.
// ROLE: Renders the sole “what converged” presentation and its bound narrative.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HERO
// purpose: Render one hero and secondary convergence rows from generated groups.
// owns:
//   - components/today-convergence/convergence-hero.tsx
// inputs: generated groups, targetDate, dayTone, contentState, and optional retry callback.
// outputs: convergence hero and public sphere/polarity selectors.
// dependencies: today-formatters, today-narrative, packages/contracts/today-convergence.ts.
// side_effects: sphere links navigate to the static sphere path; retry is delegated.
// emitted_logs: none.
// invariants: the “сошлось” copy exists only in this component and is derived from targetDate; one hero group precedes secondary rows.
// failure_policy: no hero is rendered when the caller supplies an empty group list.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HERO

// START_MODULE_MAP: M-TODAY-CONVERGENCE-HERO
// public_entrypoints:
//   - ConvergenceHero
// semantic_blocks:
//   - HERO: primary convergence group and tone marker.
//   - SECONDARY: additional canonical groups.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-HERO

import type {
  TodayConvergenceGroup,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import {
  getDayToneBackgroundClass,
  getPolarityLabel,
  getPolarityToneClasses,
  formatTargetDateRu,
  getTodaySphereLabel,
} from "./today-formatters";
import { getFacetLabel, readSignalFacet } from "@/lib/display/facet-labels";
import { TodayNarrative, type TodayNarrativeBlock } from "./today-narrative";

type Props = {
  groups: readonly TodayConvergenceGroup[];
  targetDate: TodayConvergencePayload["targetDate"];
  dayTone: TodayConvergencePayload["dayTone"];
  contentState: TodayConvergencePayload["contentState"];
  /** "full" — tone tint on the whole card (production); "band" — tint only on the header band. */
  heroVariant?: "full" | "band";
  onRetry?: () => void;
};

function groupClaims(group: TodayConvergenceGroup) {
  return [group.summary, group.meaning, group.action];
}

function SphereLink({
  sphere,
  polarity,
  className = "",
}: {
  sphere: TodayConvergenceGroup["primarySphere"];
  polarity: TodayConvergenceGroup["polarity"];
  className?: string;
}) {
  return (
    <a
      href={`/day/spheres/${sphere}`}
      data-testid={`convergence-sphere-${sphere}`}
      data-polarity={polarity}
      className={`inline-flex min-h-11 items-center gap-2 rounded-xl px-2 py-1 font-serif text-foreground transition-colors duration-150 hover:text-primary hover:no-underline focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary motion-reduce:transition-none ${className}`}
    >
      {getTodaySphereLabel(sphere)}
      <span
        className={`font-sans text-[13px] leading-[18px] ${getPolarityToneClasses(polarity)} rounded-full px-2 py-0.5 no-underline`}
      >
        {getPolarityLabel(polarity)}
      </span>
    </a>
  );
}

// START_BLOCK: HERO
export function ConvergenceHero({ groups, targetDate, dayTone, contentState, heroVariant = "full", onRetry }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HERO.ConvergenceHero
  // purpose: Render the primary convergence group, secondary rows, and bound LLM zone.
  // inputs: groups — selected generated convergence groups; targetDate — payload date for exact copy; dayTone/contentState — root axes; onRetry — LLM retry.
  // returns: hero DOM or null for an empty group list.
  // side_effects: link navigation and delegated retry callback.
  // emitted_logs: none.
  // error_behavior: empty groups produce no hero rather than a fabricated placeholder.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HERO.ConvergenceHero
  const hero = groups[0];
  if (!hero) return null;

  const secondaryGroups = groups.slice(1);
  const claims = groups.flatMap(groupClaims);
  const narrativeBlocks: TodayNarrativeBlock[] = groups
    .map((group) => {
      const facet = readSignalFacet(group);
      return {
        key: group.id,
        title: getFacetLabel(facet) ?? getTodaySphereLabel(group.primarySphere),
        facet,
        polarity: group.polarity,
        claims: groupClaims(group).filter(
          (claim): claim is NonNullable<typeof claim> => claim != null,
        ),
      };
    })
    .filter((block) => block.claims.length > 0);
  const toneBackgroundClass = getDayToneBackgroundClass(dayTone);
  const targetDateLabel = formatTargetDateRu(targetDate);
  const isBand = heroVariant === "band" && toneBackgroundClass !== "";

  return (
    <section
      data-testid="convergence-hero"
      data-day-tone={dayTone ?? undefined}
      data-evidence-level={hero.evidenceLevel}
      data-hero-variant={heroVariant}
      className={`overflow-hidden rounded-[24px] border-[1.5px] border-(--primary) ${isBand ? "bg-card" : toneBackgroundClass || "bg-card"} p-5 shadow-(--shadow-card)`}
    >
      <div className={isBand ? `-m-5 mb-5 p-5 ${toneBackgroundClass}` : ""}>
      <h2 className="font-serif text-[28px] leading-[34px] text-foreground">
        Что сошлось {targetDateLabel}
      </h2>
      <div className="mt-4 flex flex-col items-start gap-1">
        <SphereLink sphere={hero.primarySphere} polarity={hero.polarity} className="text-[22px] leading-[28px]" />
        {hero.secondarySphere ? (
          <SphereLink sphere={hero.secondarySphere} polarity={hero.polarity} className="text-[22px] leading-[28px]" />
        ) : null}
      </div>

      {secondaryGroups.length > 0 ? (
        <div className="mt-5 space-y-2">
          <p className="text-[11px] font-medium uppercase leading-[18px] tracking-[0.18em] text-muted-foreground/80">
            Также {targetDateLabel}
          </p>
          {secondaryGroups.map((group) => (
            <div
              key={group.id}
              data-testid="convergence-secondary"
              className="flex min-h-11 items-center gap-2 rounded-xl border border-border/50 px-3 py-2 text-[14px] leading-[18px]"
            >
              <SphereLink sphere={group.primarySphere} polarity={group.polarity} className="text-[15px] leading-[21px]" />
              {group.secondarySphere ? (
                <>
                  <span aria-hidden className="text-muted-foreground">·</span>
                  <SphereLink sphere={group.secondarySphere} polarity={group.polarity} className="text-[15px] leading-[21px]" />
                </>
              ) : null}
            </div>
          ))}
        </div>
      ) : null}

      <div className="mt-4 flex items-center gap-2 text-[12px] leading-[18px] text-muted-foreground/80">
        <span aria-hidden className="h-1.5 w-1.5 rounded-full bg-primary/60" />
        <span>Доказательность: {hero.evidenceLevel === "high" ? "высокая" : "средняя"}</span>
      </div>
      </div>
      <TodayNarrative state={contentState} claims={claims} blocks={narrativeBlocks} onRetry={onRetry} />
    </section>
  );
}
// END_BLOCK: HERO
