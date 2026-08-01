// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_HOW_CALCULATED — calculation disclosure.
// ROLE: Explains the deterministic Today source in a persistent accessible disclosure.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HOW-CALCULATED
// purpose: Render the static product-facing “Как это рассчитано” disclosure for ready Today screens.
// owns:
//   - components/today-convergence/how-calculated.tsx
// inputs: none.
// outputs: aria-expanded/aria-controls disclosure with hidden persistent content.
// dependencies: React state only.
// side_effects: local disclosure state.
// emitted_logs: none.
// invariants: copy is static, product-facing, and contains no implementation or provider terms.
// failure_policy: none.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HOW-CALCULATED

// START_MODULE_MAP: M-TODAY-CONVERGENCE-HOW-CALCULATED
// public_entrypoints:
//   - HowCalculated
// semantic_blocks:
//   - CALCULATION_DISCLOSURE: static product explanation.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-HOW-CALCULATED

"use client";

import { useState } from "react";

// START_BLOCK: CALCULATION_DISCLOSURE
export function HowCalculated() {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HOW-CALCULATED.HowCalculated
  // purpose: Render the collapsed calculation explanation disclosure.
  // inputs: none.
  // returns: accessible disclosure section.
  // side_effects: local open/closed state.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HOW-CALCULATED.HowCalculated
  const [open, setOpen] = useState(false);
  const contentId = "today-calculation-details";

  return (
    <section data-testid="how-calculated" className="rounded-2xl border border-border/60 bg-card/70">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-12 w-full items-center justify-between px-4 text-left text-[14px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span>Как это рассчитано</span>
        <span aria-hidden>{open ? "⌃" : "⌄"}</span>
      </button>
      <div id={contentId} hidden={!open} className="space-y-3 border-t border-border/50 px-4 py-3 text-[13px] leading-5 text-muted-foreground">
        <p>
          День считается относительно твоей натальной карты и текущего положения планет.
        </p>
        <p>
          Пик — точный момент события; окно — период его заметного действия.
        </p>
        <p>
          Возможное проявление — ориентир для наблюдения, а не гарантия того, что всё произойдёт именно так.
        </p>
      </div>
    </section>
  );
}
// END_BLOCK: CALCULATION_DISCLOSURE
