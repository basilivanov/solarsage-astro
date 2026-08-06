// ############################################################################
// AI_HEADER: MODULE_TODAY_CONVERGENCE_HOW_CALCULATED — calculation disclosure.
// ROLE: Explains the deterministic Today source in a persistent accessible disclosure.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HOW-CALCULATED
// purpose: Render the product-facing “Как это рассчитано” disclosure for ready Today screens, including deterministic payload stats and an optional interactive natal wheel.
// owns:
//   - components/today-convergence/how-calculated.tsx
// inputs: optional Today payload (fact/signal counts, birth-time mode) and optional natal preview chart.
// outputs: aria-expanded/aria-controls disclosure with stats line, static copy, and chart block.
// dependencies: NatalChartWheel; generated contracts.
// side_effects: local disclosure state.
// emitted_logs: none.
// invariants: copy is product-facing, contains no implementation or provider terms; missing payload/chart omits the corresponding block instead of fabricating numbers.
// failure_policy: none.
// END_MODULE_CONTRACT: M-TODAY-CONVERGENCE-HOW-CALCULATED

// START_MODULE_MAP: M-TODAY-CONVERGENCE-HOW-CALCULATED
// public_entrypoints:
//   - HowCalculated
// semantic_blocks:
//   - CALCULATION_DISCLOSURE: stats line, static product explanation, natal wheel.
// owned_tests:
//   - __tests__/components/today-convergence/today-screen.test.tsx
// END_MODULE_MAP: M-TODAY-CONVERGENCE-HOW-CALCULATED

"use client";

import { useEffect, useState } from "react";
import { ChevronDown } from "lucide-react";
import type { TodayConvergencePayload } from "@/packages/contracts/today-convergence";
import type { NatalPreviewChart } from "@/lib/contracts/natal";
import { NatalChartWheel } from "@/components/readings/natal-chart-wheel";

type Props = {
  payload?: TodayConvergencePayload;
  chart?: NatalPreviewChart | null;
};

function birthTimeNote(payload: TodayConvergencePayload): string {
  const mode = payload.birthTime.mode;
  if (mode === "exact") return "Время рождения точное: дома, окна и пики считаются полностью.";
  if (mode === "bucket") return "Время рождения примерное: дома и пики считаются с запасом, точность окон снижена.";
  return "Время рождения неизвестно: расчёт без домов, точность окон минимальная.";
}

// START_BLOCK: CALCULATION_DISCLOSURE
export function HowCalculated({ payload, chart }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HOW_CALCULATED.HowCalculated
  // purpose: Render the collapsed calculation explanation disclosure with payload stats and an optional natal wheel.
  // inputs: payload — Today envelope for deterministic counts; chart — optional natal preview chart for the wheel.
  // returns: accessible disclosure section.
  // side_effects: local open/closed state.
  // emitted_logs: none.
  // error_behavior: missing payload/chart simply omits the corresponding block.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONVERGENCE-HOW_CALCULATED.HowCalculated
  const [open, setOpen] = useState(false);
  // The wheel computes SVG coordinates with Math.sin/cos, which differ by 1 ULP
  // between Node SSR and the browser and would trip hydration; render it client-only.
  const [mounted, setMounted] = useState(false);
  useEffect(() => setMounted(true), []);
  const contentId = "today-calculation-details";

  const factsCount = payload?.events.length ?? 0;
  const signalsCount = payload
    ? payload.state === "convergence_today"
      ? payload.convergences.length
      : payload.impulses.length + (payload.mainEvent ? 1 : 0)
    : 0;

  return (
    <section data-testid="how-calculated" className="rounded-[24px] border border-border/40 bg-card shadow-(--shadow-card)">
      <button
        type="button"
        aria-expanded={open}
        aria-controls={contentId}
        onClick={() => setOpen((value) => !value)}
        className="flex min-h-12 w-full items-center justify-between px-4 text-left text-[14px] font-medium focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary"
      >
        <span>Как это рассчитано</span>
        <ChevronDown
          aria-hidden
          className={`h-4 w-4 text-muted-foreground transition-transform duration-200 ${open ? "rotate-180" : ""} motion-reduce:transition-none`}
        />
      </button>
      <div id={contentId} hidden={!open} className="space-y-3 border-t border-border/50 px-4 py-3 text-[13px] leading-5 text-muted-foreground">
        {payload ? (
          <p data-testid="how-calculated-stats">
            Для этого дня собрано {factsCount} физических факта неба; из них по правилам
            доказательности отобрано {signalsCount} публичных сигнала. {birthTimeNote(payload)}
          </p>
        ) : null}
        <p>
          День считается относительно твоей натальной карты и текущего положения планет.
        </p>
        <p>
          Пик — точный момент события; окно — период его заметного действия.
        </p>
        <p>
          Возможное проявление — ориентир для наблюдения, а не гарантия того, что всё произойдёт именно так.
        </p>
        {chart && mounted ? (
          <div data-testid="how-calculated-chart" className="-mx-4">
            <NatalChartWheel chart={chart} />
          </div>
        ) : null}
      </div>
    </section>
  );
}
// END_BLOCK: CALCULATION_DISCLOSURE
