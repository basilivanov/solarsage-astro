// ############################################################################
// AI_HEADER: MODULE_TODAY_HORIZON_TECHNIQUE_DISCLOSURE — per-card technical disclosure for backend horizons.
// ROLE: Keeps technical terms inside an explicit expandable region for one backend horizon card.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE
// purpose: Render a stable, accessible per-horizon technical explanation disclosure.
// owns:
//   - components/today/horizon-technique-disclosure.tsx
// inputs: explanations - backend technique explanations; horizon - required generated horizon type.
// outputs: wrapper/toggle/region data-horizon, unique toggle id/aria-controls, region role/aria-labelledby.
// dependencies: react useId/useState, lib/contracts/today, lucide-react.
// side_effects: local disclosure state only.
// emitted_logs: none.
// invariants:
//   - technical vocabulary appears only inside opened content.
//   - aria-expanded/aria-controls/role=region stay in sync.
//   - single useId suffix owns toggle/region pair.
//   - required generated horizon repeated on wrapper/toggle/region.
//   - closed content absent from DOM.
//   - backend explanations/timing preserve order/copy.
// failure_policy: none.
// END_MODULE_CONTRACT: M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE

// START_MODULE_MAP: M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE
// public_entrypoints:
//   - HorizonTechniqueDisclosure
// semantic_blocks:
//   - DISCLOSURE: accessible per-card calculation explanation.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE

"use client"

import { useId, useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import type { TodayV2TechniqueExplanation, TodayV2Horizon } from "@/lib/contracts/today"

type HorizonType = TodayV2Horizon["horizon"]

// START_BLOCK: DISCLOSURE
export function HorizonTechniqueDisclosure({
  explanations,
  horizon,
}: {
  explanations: TodayV2TechniqueExplanation[]
  horizon: HorizonType
}) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE.HorizonTechniqueDisclosure
  // purpose: Render one accessible backend technique disclosure for a single horizon card.
  // inputs: explanations - backend technique explanation list; horizon - required closed horizon type.
  // returns: disclosure JSX.
  // side_effects: stores local expanded/collapsed state.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-TECHNIQUE-DISCLOSURE.HorizonTechniqueDisclosure
  const [open, setOpen] = useState(false)
  const idSuffix = useId().replace(/:/g, "-")
  const toggleId = `tech-toggle-${horizon}-${idSuffix}`
  const regionId = `tech-region-${horizon}-${idSuffix}`

  return (
    <div className="mt-4 rounded-2xl border border-violet-200/80 bg-violet-50/45 dark:border-violet-400/20 dark:bg-violet-500/10" data-horizon={horizon}>
      <button
        type="button"
        id={toggleId}
        data-testid="why-horizon-technical-toggle"
        data-horizon={horizon}
        aria-expanded={open}
        aria-controls={regionId}
        onClick={() => setOpen(!open)}
        className="flex min-h-12 w-full items-center justify-between gap-3 px-4 py-3 text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-inset"
      >
        <span className="text-[14px] font-medium text-foreground">Как это рассчитано</span>
        {open ? <ChevronUp className="h-4 w-4 flex-none" aria-hidden /> : <ChevronDown className="h-4 w-4 flex-none" aria-hidden />}
      </button>
      {open ? (
        <div
          id={regionId}
          role="region"
          aria-labelledby={toggleId}
          data-testid="why-horizon-technical-content"
          data-horizon={horizon}
          className="border-t border-violet-200/80 px-4 pb-4 pt-3 dark:border-violet-400/20"
        >
          <div className="space-y-4">
            {explanations.map((item, index) => (
              <section key={`${item.technique}-${index}`} className="space-y-2 rounded-xl border border-border/60 bg-card/80 p-3">
                <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-700 dark:text-violet-200">{item.label}</p>
                <p className="text-[14px] leading-relaxed text-foreground/85">{item.whatItIs}</p>
                <p className="text-[14px] leading-relaxed text-foreground/85">{item.whyItMattersNow}</p>
                {item.timing ? (
                  <div className="rounded-xl border border-border/60 bg-background/70 px-3 py-2 text-[13px] text-muted-foreground">
                    <p>{item.timing.rangeLabel}</p>
                    {item.timing.peakLabel ? <p>{item.timing.peakLabel}</p> : null}
                    <p>{item.timing.stateLabel}</p>
                  </div>
                ) : null}
              </section>
            ))}
          </div>
        </div>
      ) : null}
    </div>
  )
}
// END_BLOCK: DISCLOSURE
