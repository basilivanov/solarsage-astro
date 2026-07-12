// ############################################################################
// AI_HEADER: MODULE_TODAY_HORIZON_ACTIONS — backend-owned horizon action lists.
// ROLE: Renders do/avoid lists from the additive TodayV2 horizon contract with no local inference.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-HORIZON-ACTIONS
// purpose: Render backend-owned heading, validity label, and ordered do/avoid lists for one horizon card.
// owns:
//   - components/today/horizon-actions.tsx
// inputs: actions - TodayV2HorizonActions wire model.
// outputs: stable why-horizon-actions and why-horizon-avoid DOM blocks.
// dependencies: lib/contracts/today.
// side_effects: none.
// emitted_logs: none.
// invariants:
//   - preserves backend order exactly.
//   - performs no generated advice, sorting, or text inference.
// failure_policy: renders empty nothing only when caller omits the component.
// END_MODULE_CONTRACT: M-TODAY-HORIZON-ACTIONS

// START_MODULE_MAP: M-TODAY-HORIZON-ACTIONS
// public_entrypoints:
//   - HorizonActions
// semantic_blocks:
//   - ACTION_LISTS: ordered do/avoid rendering and validity label.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-HORIZON-ACTIONS

import type { TodayV2HorizonActions } from "@/lib/contracts/today"

// START_BLOCK: ACTION_LISTS
export function HorizonActions({ actions }: { actions: TodayV2HorizonActions }) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-ACTIONS.HorizonActions
  // purpose: Render one backend-owned action block without reordering or copy generation.
  // inputs: actions - TodayV2HorizonActions.
  // returns: JSX fragment with do and avoid lists.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: none.
  // END_FUNCTION_CONTRACT: F-M-TODAY-HORIZON-ACTIONS.HorizonActions
  return (
    <div className="mt-4 space-y-3">
      <div className="rounded-2xl border border-violet-200/80 bg-card/80 p-3 dark:border-violet-400/25">
        <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-700 dark:text-violet-200">{actions.heading}</p>
        <p className="mt-1 text-[13px] text-muted-foreground">{actions.validUntilLabel}</p>
      </div>

      <div data-testid="why-horizon-actions" className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-3 dark:border-emerald-400/20 dark:bg-emerald-500/10">
        <p className="text-[12px] font-semibold text-foreground">Что сделать</p>
        <ol className="mt-2 space-y-2 text-[14px] leading-relaxed text-foreground/85">
          {actions.do.map((item) => (
            <li key={item.id} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-emerald-600 dark:bg-emerald-300" aria-hidden />
              <span>{item.text}</span>
            </li>
          ))}
        </ol>
      </div>

      <div data-testid="why-horizon-avoid" className="rounded-2xl border border-amber-200/80 bg-amber-50/55 p-3 dark:border-amber-400/20 dark:bg-amber-500/10">
        <p className="text-[12px] font-semibold text-foreground">Чего лучше не делать</p>
        <ol className="mt-2 space-y-2 text-[14px] leading-relaxed text-foreground/85">
          {actions.avoid.map((item) => (
            <li key={item.id} className="flex gap-2">
              <span className="mt-1 h-1.5 w-1.5 flex-none rounded-full bg-amber-600 dark:bg-amber-300" aria-hidden />
              <span>{item.text}</span>
            </li>
          ))}
        </ol>
      </div>
    </div>
  )
}
// END_BLOCK: ACTION_LISTS
