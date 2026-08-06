// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_NARRATIVE — LLM-owned Today copy zone.
// ROLE: Renders only bound claim text and explicit pending/unavailable states.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-NARRATIVE
// purpose: Render the Today LLM zone for ready, pending, unavailable, or not-needed content without blocking deterministic facts.
// owns:
//   - components/today-convergence/today-narrative.tsx
// inputs: generated narrative claims, contentState, optional per-signal blocks, and optional retry callback.
// outputs: accessible data-testid=today-narrative DOM contract.
// dependencies: packages/contracts/today-convergence.ts.
// side_effects: invokes onRetry only after an explicit user click.
// emitted_logs: none.
// invariants: ready output is claim.text only; pending skeleton stays inside this zone.
// failure_policy: unavailable is honest polite status copy with a retry action; not_needed renders nothing.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-NARRATIVE

// START_MODULE_MAP: M-TODAY-CONVERGENCE-NARRATIVE
// public_entrypoints:
//   - TodayNarrative
// semantic_blocks:
//   - NARRATIVE_STATE: state-specific LLM presentation.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-NARRATIVE

import type {
  TodayConvergenceGroup,
  TodayConvergenceNarrativeClaim,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";
import { getPolarityLabel, getPolarityToneClasses } from "./today-formatters";

/** One selected signal's narrative: facet/sphere header, its polarity, its claims. */
export type TodayNarrativeBlock = {
  key: string;
  title: string;
  facet: string | null;
  polarity: TodayConvergenceGroup["polarity"];
  claims: readonly TodayConvergenceNarrativeClaim[];
};

type Props = {
  state: TodayConvergencePayload["contentState"];
  claims: readonly (TodayConvergenceNarrativeClaim | null | undefined)[];
  /** Structured per-signal blocks; when present, ready state renders blocks instead of the flat claim list. */
  blocks?: readonly TodayNarrativeBlock[];
  onRetry?: () => void;
};

// START_BLOCK: NARRATIVE_STATE
export function TodayNarrative({ state, claims, blocks, onRetry }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-NARRATIVE.TodayNarrative
  // purpose: Render only the LLM-owned state permitted by the payload.
  // inputs: state — generated contentState; claims — nullable bound claims; onRetry — optional retry callback.
  // returns: narrative DOM or null for not_needed/empty ready content.
  // side_effects: calls onRetry from the unavailable button.
  // emitted_logs: none.
  // error_behavior: never fabricates fallback narrative text.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-NARRATIVE.TodayNarrative
  if (state === "not_needed") return null;

  const visibleClaims = claims.filter(
    (claim): claim is TodayConvergenceNarrativeClaim => claim != null,
  );

  if (state === "ready" && visibleClaims.length === 0 && (!blocks || blocks.length === 0)) return null;

  return (
    <section
      data-testid="today-narrative"
      data-state={state}
      aria-live={state === "pending" || state === "unavailable" ? "polite" : undefined}
      className="rounded-[24px] border border-border/40 bg-card p-4 text-[15px] leading-[24px] text-pretty text-foreground/90 shadow-(--shadow-card)"
    >
      {state === "ready" ? (
        blocks && blocks.length > 0 ? (
          <div className="space-y-5">
            {blocks.map((block) => (
              <div
                key={block.key}
                data-testid="today-narrative-block"
                data-polarity={block.polarity}
                data-facet={block.facet ?? undefined}
              >
                <div className="flex flex-wrap items-center gap-2">
                  <span className="font-medium text-foreground">{block.title}</span>
                  <span
                    className={`rounded-full px-2 py-0.5 text-[12px] leading-[18px] ${getPolarityToneClasses(block.polarity)}`}
                  >
                    {getPolarityLabel(block.polarity)}
                  </span>
                </div>
                <div className="mt-2 space-y-3">
                  {block.claims.map((claim, index) => (
                    <p key={`${claim.sourceEventIds.join("-")}-${index}`}>{claim.text}</p>
                  ))}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="space-y-3">
            {visibleClaims.map((claim, index) => (
              <p key={`${claim.sourceEventIds.join("-")}-${index}`}>{claim.text}</p>
            ))}
          </div>
        )
      ) : null}

      {state === "pending" ? (
        <div role="status" aria-live="polite" aria-label="Готовим персональный разбор">
          <span aria-hidden className="block h-4 w-4/5 animate-pulse rounded bg-muted" />
          <span aria-hidden className="mt-2 block h-4 w-3/5 animate-pulse rounded bg-muted" />
        </div>
      ) : null}

      {state === "unavailable" ? (
        <div
          data-testid="today-narrative-unavailable"
          className="flex flex-col items-start gap-3"
          role="status"
          aria-live="polite"
        >
          <p>Дополнительный разбор пока недоступен</p>
          <p className="text-[13px] leading-5 text-muted-foreground">
            Основные факты и события уже доступны на экране. Можно повторить попытку.
          </p>
          <button
            type="button"
            onClick={() => onRetry?.()}
            className="min-h-11 rounded-full border border-border/70 bg-background px-4 text-[13px] font-medium text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
          >
            Повторить
          </button>
        </div>
      ) : null}
    </section>
  );
}
// END_BLOCK: NARRATIVE_STATE
