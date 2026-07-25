// ############################################################################
// AI_HEADER: MODULE_TODAY_CONCRETE_DAY_ADVICE — human-first 12-sphere navigator.
// ROLE: Renders every backend-owned advice row as a controlled two-column
//       navigator and shows one non-technical details panel at a time.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE
// purpose: Present all concrete advice rows without hiding, re-ranking, or calculating them.
// owns:
//   - components/today/concrete-day-advice.tsx
// inputs: concreteAdvice, selectedKey, onSelectedKeyChange, onWhyOpen.
// outputs: data-testid="concrete-day-advice" with controlled sphere buttons and visible semantic verdict statuses.
// dependencies: lib/contracts/today, lib/icons, lib/presentation/today-v2.
// side_effects: delegates selection and Why disclosure to TodayScreen.
// emitted_logs: none.
// invariants:
//   - every received row is visible in canonical adapter order.
//   - only one details panel can exist.
//   - human navigator never renders evidence, techniques, planets, or orbs.
//   - compact rows and details share one normalized verdict presentation map and public data-status contract.
//   - Exact 4 visible verdict mappings (good/neutral/caution/avoid); color secondary.
//   - data-status stays exact backend verdict enum; unknown falls back to neutral.
// failure_policy: render only supplied rows when the payload is incomplete.
// END_MODULE_CONTRACT: M-TODAY-CONCRETE-DAY-ADVICE

// START_MODULE_MAP: M-TODAY-CONCRETE-DAY-ADVICE
// public_entrypoints:
//   - ConcreteDayAdvice
//   - normalizeConcreteAdviceVerdict
// semantic_blocks:
//   - VERDICT_PRESENTATION: normalized compact/details semantic status metadata.
//   - SPHERE_NAVIGATOR: controlled 12-sphere selection and visible status rows.
//   - SPHERE_DETAILS: selected sphere's full status badge and human guidance.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
//   - e2e/dev-visible-sphere-status.spec.ts
// END_MODULE_MAP: M-TODAY-CONCRETE-DAY-ADVICE

"use client"

import { ChevronDown, ChevronUp } from "lucide-react"
import type { ConcreteAdviceBlock, ConcreteAdviceRow } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"
import { getHumanSphereLabel, getVerdictManifestationCopy } from "@/lib/presentation/today-v2"

type Props = {
  concreteAdvice: ConcreteAdviceBlock
  selectedKey: string | null
  onSelectedKeyChange: (key: string | null) => void
  onWhyOpen: () => void
}

type Verdict = "good" | "caution" | "avoid" | "neutral"

const CONCRETE_ADVICE_VERDICT_PRESENTATION: Record<Verdict, {
  dotClass: string
  iconShellClass: string
  compactCopy: string
  detailsCopy: string
  statusTextClass: string
  badgeClass: string
}> = {
  good: {
    dotClass: "bg-emerald-500",
    iconShellClass: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-200",
    compactCopy: "Поддержка",
    detailsCopy: "Поддерживающий сигнал",
    statusTextClass: "text-emerald-700 dark:text-emerald-200",
    badgeClass: "border-emerald-200 bg-emerald-50 text-emerald-800 dark:border-emerald-400/30 dark:bg-emerald-500/15 dark:text-emerald-100",
  },
  caution: {
    dotClass: "bg-amber-500",
    iconShellClass: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-200",
    compactCopy: "Требует внимания",
    detailsCopy: "Напряжённый сигнал · требует внимания",
    statusTextClass: "text-amber-700 dark:text-amber-200",
    badgeClass: "border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-400/30 dark:bg-amber-500/15 dark:text-amber-100",
  },
  avoid: {
    dotClass: "bg-rose-500",
    iconShellClass: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-200",
    compactCopy: "Лучше отложить",
    detailsCopy: "Сильное напряжение · лучше отложить",
    statusTextClass: "text-rose-700 dark:text-rose-200",
    badgeClass: "border-rose-200 bg-rose-50 text-rose-800 dark:border-rose-400/30 dark:bg-rose-500/15 dark:text-rose-100",
  },
  neutral: {
    dotClass: "bg-violet-500",
    iconShellClass: "bg-violet-50 text-violet-700 dark:bg-violet-500/15 dark:text-violet-200",
    compactCopy: "Ровный фон",
    detailsCopy: "Нейтральный сигнал",
    statusTextClass: "text-violet-700 dark:text-violet-200",
    badgeClass: "border-violet-200 bg-violet-50 text-violet-800 dark:border-violet-400/30 dark:bg-violet-500/15 dark:text-violet-100",
  },
}

// START_BLOCK: VERDICT_PRESENTATION
export function normalizeConcreteAdviceVerdict(verdict: string | null | undefined): Verdict {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.normalizeConcreteAdviceVerdict
  // purpose: Normalize string verdicts from the API to the valid Verdict union.
  // inputs: verdict — raw string value.
  // returns: Verdict — normalized value ("good", "caution", "avoid", "neutral").
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns "neutral" as fallback.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.normalizeConcreteAdviceVerdict
  return verdict && verdict in CONCRETE_ADVICE_VERDICT_PRESENTATION ? verdict as Verdict : "neutral"
}
// END_BLOCK: VERDICT_PRESENTATION

function pairRows(rows: ConcreteAdviceRow[]): ConcreteAdviceRow[][] {
  const pairs: ConcreteAdviceRow[][] = []
  for (let index = 0; index < rows.length; index += 2) pairs.push(rows.slice(index, index + 2))
  return pairs
}

function sphereButtonId(key: string): string {
  return `concrete-sphere-${key}`
}

function detailsId(key: string): string {
  return `concrete-advice-details-${key}`
}

// START_BLOCK: SPHERE_NAVIGATOR
export function ConcreteDayAdvice({
  concreteAdvice,
  selectedKey,
  onSelectedKeyChange,
  onWhyOpen,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  // purpose: Render a controlled 12-sphere navigator and one selected details panel.
  // inputs: Props — backend rows plus parent-owned selected key and Why callback.
  // returns: Navigator JSX.
  // side_effects: invokes parent callbacks from native buttons.
  // emitted_logs: none.
  // error_behavior: incomplete payloads render their available rows without fabricated entries.
  // END_FUNCTION_CONTRACT: F-M-TODAY-CONCRETE-DAY-ADVICE.ConcreteDayAdvice
  const rows = concreteAdvice?.rows || []

  return (
    <section
      className="px-5"
      aria-label="Быстрый навигатор по 12 сферам"
      data-testid="concrete-day-advice"
    >
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted-foreground">
        Конкретно сегодня
      </p>
      <h2 className="mt-1 font-serif text-[24px] leading-tight text-foreground">Быстрый навигатор по 12 сферам</h2>

      <div className="mt-4 grid grid-cols-2 gap-2.5">
        {pairRows(rows).map((pair) => {
          const selectedRow = pair.find((row) => row.key === selectedKey) || null
          return (
            <div key={pair.map((row) => row.key).join("-")} className="col-span-2 grid grid-cols-2 gap-2.5">
              {pair.map((row) => {
                const verdict = normalizeConcreteAdviceVerdict(row.verdict)
                const meta = CONCRETE_ADVICE_VERDICT_PRESENTATION[verdict]
                const Icon = getIcon(row.iconName)
                const selected = row.key === selectedKey
                return (
                  <button
                    key={row.key}
                    id={sphereButtonId(row.key)}
                    type="button"
                    data-testid="concrete-day-advice-row"
                    data-sphere-key={row.key}
                    data-status={verdict}
                    data-selected={selected ? "true" : "false"}
                    aria-expanded={selected}
                    aria-controls={detailsId(row.key)}
                    onClick={() => onSelectedKeyChange(selected ? null : row.key)}
                    className={`flex min-h-[88px] min-w-0 items-center gap-2.5 rounded-2xl border bg-card px-3 text-left transition focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 ${
                      selected
                        ? "border-violet-500 bg-violet-50/60 shadow-[0_0_0_1px_rgba(139,92,246,0.25),0_14px_30px_-24px_rgba(109,40,217,0.75)] dark:border-violet-300 dark:bg-violet-500/15"
                        : "border-border/70 hover:border-violet-300 hover:bg-violet-50/30 dark:hover:bg-violet-500/10"
                    }`}
                  >
                    <span className={`flex h-8 w-8 flex-none items-center justify-center rounded-xl ${meta.iconShellClass}`}>
                      <Icon className="h-4 w-4" strokeWidth={1.8} aria-hidden />
                    </span>
                    <span className="min-w-0 flex-1">
                      <span className="block text-[14px] font-semibold leading-snug text-foreground">{row.label}</span>
                      <span data-testid="concrete-day-advice-row-status" data-status={verdict} className={`mt-0.5 block text-[12px] font-semibold leading-snug ${meta.statusTextClass}`}>{meta.compactCopy}</span>
                    </span>
                    <span className="flex flex-none flex-col items-center gap-1.5">
                      <span className={`h-2 w-2 rounded-full ${meta.dotClass}`} aria-hidden />
                      {selected ? (
                        <ChevronUp className="h-4 w-4 text-violet-700 dark:text-violet-200" aria-hidden />
                      ) : (
                        <ChevronDown className="h-4 w-4 text-muted-foreground" aria-hidden />
                      )}
                    </span>
                  </button>
                )
              })}

              {selectedRow ? (
                <SphereDetails
                  row={selectedRow}
                  onWhyOpen={onWhyOpen}
                  onClose={() => onSelectedKeyChange(null)}
                />
              ) : null}
            </div>
          )
        })}
      </div>
    </section>
  )
}
// END_BLOCK: SPHERE_NAVIGATOR

function SphereDetails({
  row,
  onWhyOpen,
  onClose,
}: {
  row: ConcreteAdviceRow
  onWhyOpen: () => void
  onClose: () => void
}) {
  const label = getHumanSphereLabel(row)
  const verdict = normalizeConcreteAdviceVerdict(row.verdict)
  const meta = CONCRETE_ADVICE_VERDICT_PRESENTATION[verdict]
  const hasEvidence = (row.evidence || []).length > 0
  return (
    <section
      id={detailsId(row.key)}
      data-testid="concrete-day-advice-details"
      data-sphere-key={row.key}
      data-status={verdict}
      role="region"
      aria-labelledby={sphereButtonId(row.key)}
      className="col-span-2 rounded-2xl border border-violet-200/80 bg-card px-4 py-4 shadow-[0_18px_36px_-30px_rgba(109,40,217,0.65)] dark:border-violet-400/30"
    >
      <h3 className="font-serif text-[25px] leading-tight text-foreground">{label}</h3>
      <span data-testid="concrete-day-advice-details-status" data-status={verdict} className={`mt-2 inline-flex rounded-full border px-2.5 py-1 text-[12px] font-semibold ${meta.badgeClass}`}>{meta.detailsCopy}</span>
      <div className="mt-4 border-b border-border/60 pb-4">
        <h4 className="text-[15px] font-semibold text-violet-700 dark:text-violet-200">Что может проявиться</h4>
        <p className="mt-1.5 text-[15px] leading-relaxed text-muted-foreground">
          {getVerdictManifestationCopy(row.verdict)}
        </p>
      </div>
      {row.text ? (
        <div className="mt-4">
          <h4 className="text-[15px] font-semibold text-violet-700 dark:text-violet-200">Что поможет</h4>
          <p className="mt-1.5 text-[15px] leading-relaxed text-foreground/85">{row.text}</p>
        </div>
      ) : null}
      {hasEvidence ? (
        <p className="mt-4 rounded-xl bg-violet-50/70 px-3 py-2 text-[13px] leading-relaxed text-violet-900 dark:bg-violet-500/10 dark:text-violet-100">
          Объяснение основано на вашей личной карте
        </p>
      ) : null}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          type="button"
          data-testid="sphere-why-cta"
          onClick={onWhyOpen}
          className="min-h-11 rounded-xl border border-violet-300 bg-violet-50 px-3 text-[14px] font-semibold text-violet-800 transition hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2 dark:border-violet-400/40 dark:bg-violet-500/15 dark:text-violet-100"
        >
          Почему это про меня
        </button>
        <button
          type="button"
          onClick={onClose}
          className="min-h-11 rounded-xl px-3 text-[14px] font-medium text-muted-foreground transition hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-offset-2"
        >
          Свернуть
        </button>
      </div>
    </section>
  )
}
