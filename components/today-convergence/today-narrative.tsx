// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_NARRATIVE — LLM-owned Today copy zone.
// ROLE: Renders only bound claim text and explicit pending/unavailable states.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-NARRATIVE
// purpose: Render the Today LLM zone for ready, pending, unavailable, or not-needed content without blocking deterministic facts.
// owns:
//   - components/today-convergence/today-narrative.tsx
// inputs: generated narrative claims, contentState, and optional retry callback.
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
  TodayConvergenceNarrativeClaim,
  TodayConvergencePayload,
} from "@/packages/contracts/today-convergence";

type Props = {
  state: TodayConvergencePayload["contentState"];
  claims: readonly (TodayConvergenceNarrativeClaim | null | undefined)[];
  onRetry?: () => void;
};

// START_BLOCK: NARRATIVE_STATE
export function TodayNarrative({ state, claims, onRetry }: Props) {
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

  if (state === "ready" && visibleClaims.length === 0) return null;

  return (
    <section
      data-testid="today-narrative"
      data-state={state}
      aria-live={state === "pending" || state === "unavailable" ? "polite" : undefined}
      className="rounded-[24px] border border-border/40 bg-card p-4 text-[15px] leading-[24px] text-pretty text-foreground/90 shadow-(--shadow-card)"
    >
      {state === "ready" ? (
        <div className="space-y-3">
          {visibleClaims.map((claim, index) => (
            <p key={`${claim.sourceEventIds.join("-")}-${index}`}>{claim.text}</p>
          ))}
        </div>
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
