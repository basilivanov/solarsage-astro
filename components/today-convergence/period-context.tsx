// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_PERIOD_CONTEXT — quiet-day period disclosure.
// ROLE: Keeps deterministic period context in the DOM while exposing disclosure state.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PERIOD-CONTEXT
// purpose: Render active/no-accent period context with accessible disclosure semantics.
// owns:
//   - components/today-convergence/period-context.tsx
// inputs: generated TodayConvergencePeriodContext.
// outputs: button aria-expanded/aria-controls and hidden persistent content.
// dependencies: packages/contracts/today-convergence.ts.
// side_effects: local disclosure state only.
// emitted_logs: none.
// invariants: collapsing toggles hidden and never removes the content node.
// failure_policy: title is shown as received; no LLM fallback is invented.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-PERIOD-CONTEXT

// START_MODULE_MAP: M-TODAY-CONVERGENCE-PERIOD-CONTEXT
// public_entrypoints:
//   - PeriodContext
// semantic_blocks:
//   - PERIOD_DISCLOSURE: deterministic period details and disclosure control.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-PERIOD-CONTEXT

"use client";

import { useState } from "react";
import type { TodayConvergencePeriodContext } from "@/packages/contracts/today-convergence";

type Props = { context: TodayConvergencePeriodContext };

// START_BLOCK: PERIOD_DISCLOSURE
export function PeriodContext({ context }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PERIOD-CONTEXT.PeriodContext
  // purpose: Render a collapsed-by-default period context disclosure.
  // inputs: context — generated period context object.
  // returns: disclosure section with persistent hidden content.
  // side_effects: local open/closed state.
  // emitted_logs: none.
  // error_behavior: null title is rendered as an empty detail rather than fabricated copy.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-PERIOD-CONTEXT.PeriodContext
  const [open, setOpen] = useState(false);
  const contentId = "today-period-context-details";

  return (
    <section data-testid="period-context" className="rounded-[24px] border border-border/40 bg-card shadow-(--shadow-card)">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-12 w-full items-center justify-between px-4 text-left text-[14px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span>Контекст периода</span>
        <span aria-hidden className="text-muted-foreground">{open ? "⌃" : "⌄"}</span>
      </button>
      <div id={contentId} hidden={!open} className="border-t border-border/50 px-4 py-3 text-[13px] text-muted-foreground">
        <p>{context.title}</p>
        {context.kind === "active_period" && context.activeFrom && context.activeUntil ? (
          <p className="mt-1">Активен с {context.activeFrom} по {context.activeUntil}.</p>
        ) : null}
      </div>
    </section>
  );
}
// END_BLOCK: PERIOD_DISCLOSURE
