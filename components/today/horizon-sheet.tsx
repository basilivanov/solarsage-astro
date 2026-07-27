// ############################################################################
// AI_HEADER: MODULE_TODAY_HORIZON_SHEET
// ROLE: BottomSheet modal component for a single horizon's full story.
// DEPENDENCIES: react, components/ui/sheet, lib/contracts/today, lib/presentation/today-v2.
// GRACE_ANCHORS: [HORIZON_SHEET]
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-HORIZON-SHEET
// purpose: Render an instant bottom-sheet modal for one selected backend horizon.
// owns:
//   - components/today/horizon-sheet.tsx
// inputs: horizon (TodayV2Horizon | null), concreteAdvice, onSphereSelect, onClose.
// outputs: Sheet modal with data-testid="horizon-sheet".
// dependencies: components/ui/sheet, lib/contracts/today, horizon-actions, horizon-technique-disclosure.
// side_effects: opens/closes Radix Sheet modal, delegates sphere navigation to onSphereSelect after closing.
// emitted_logs: none.
// failure_policy: renders gracefully from provided horizon prop.
// END_MODULE_CONTRACT: M-TODAY-HORIZON-SHEET

// START_MODULE_MAP: M-TODAY-HORIZON-SHEET
// public_entrypoints:
//   - HorizonSheet
// semantic_blocks:
//   - HORIZON_SHEET_RENDER: render Radix Sheet bottom modal with full horizon details.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-HORIZON-SHEET

"use client"

import React from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import type { ConcreteAdviceBlock, TodayV2Horizon } from "@/lib/contracts/today"
import { HorizonActions } from "./horizon-actions"
import { HorizonTechniqueDisclosure } from "./horizon-technique-disclosure"

const HORIZON_INDEX = { long: "01", medium: "02", fast: "03" } as const

const BACKEND_TONE_LABELS = {
  supportive: "Поддерживает",
  neutral: "Ровный фон",
  tense: "Требует внимания",
  mixed: "Смешанный сигнал",
} as const

const BACKEND_TONE_STYLES = {
  supportive: {
    badge: "bg-emerald-100 text-emerald-800 dark:bg-emerald-500/20 dark:text-emerald-100",
    timing: "border-emerald-200/80 bg-emerald-50/50 dark:border-emerald-400/20 dark:bg-emerald-500/10",
    eyebrow: "text-emerald-700 dark:text-emerald-200",
  },
  neutral: {
    badge: "bg-slate-200/80 text-slate-800 dark:bg-zinc-500/20 dark:text-zinc-100",
    timing: "border-slate-200/80 bg-slate-100/70 dark:border-zinc-400/20 dark:bg-zinc-500/10",
    eyebrow: "text-slate-700 dark:text-zinc-200",
  },
  tense: {
    badge: "bg-rose-100 text-rose-800 dark:bg-rose-500/20 dark:text-rose-100",
    timing: "border-rose-200/80 bg-rose-50/60 dark:border-rose-400/20 dark:bg-rose-500/10",
    eyebrow: "text-rose-700 dark:text-rose-200",
  },
  mixed: {
    badge: "bg-violet-100 text-violet-800 dark:bg-violet-500/15 dark:text-violet-100",
    timing: "border-violet-200/80 bg-violet-50/45 dark:border-violet-400/20 dark:bg-violet-500/10",
    eyebrow: "text-violet-700 dark:text-violet-200",
  },
} as const

interface HorizonSheetProps {
  horizon: TodayV2Horizon | null
  concreteAdvice?: ConcreteAdviceBlock | null
  onSphereSelect?: (key: string) => void
  onClose: () => void
}

// START_BLOCK: HORIZON_SHEET_RENDER
export function HorizonSheet({
  horizon,
  concreteAdvice,
  onSphereSelect,
  onClose,
}: HorizonSheetProps) {
  const isOpen = Boolean(horizon)

  if (!horizon) return null

  const index = HORIZON_INDEX[horizon.horizon]
  const toneStyle = BACKEND_TONE_STYLES[horizon.tone]
  const adviceRows = concreteAdvice?.rows ?? []
  const sphereRows = horizon.likelySpheres
    .map((key) => adviceRows.find((row) => row.key === key))
    .filter((row): row is NonNullable<typeof row> => Boolean(row))

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="bottom"
        data-testid="horizon-sheet"
        data-horizon={horizon.horizon}
        data-status={horizon.tone}
        data-timing-state={horizon.timing.state}
        className="rounded-t-[24px] border-t border-border/60 bg-card max-h-[85dvh] flex flex-col p-0 outline-none"
      >
        {/* Grabber bar */}
        <div className="w-12 h-1 bg-border/80 rounded-full mx-auto mt-3 mb-1 flex-none" aria-hidden="true" />

        <div className="overflow-y-auto px-6 py-4 space-y-5 flex-1">
          <SheetHeader className="p-0 space-y-0">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <span
                  data-testid="why-horizon-index"
                  className="inline-flex h-6 w-6 items-center justify-center rounded-full bg-violet-100 text-[11px] font-semibold text-violet-700 dark:bg-violet-500/15 dark:text-violet-100"
                >
                  {index}
                </span>
                <p className={`mt-1 text-[11px] font-semibold uppercase tracking-[0.14em] ${toneStyle.eyebrow}`}>
                  {horizon.eyebrow}
                </p>
                <SheetTitle className="mt-1 font-serif text-[24px] leading-[1.22] text-foreground m-0">
                  {horizon.title}
                </SheetTitle>
              </div>
              <span
                data-testid="why-horizon-tone"
                data-status={horizon.tone}
                className={`max-w-full whitespace-normal text-center flex-none rounded-full px-2.5 py-1 text-[11px] font-medium ${toneStyle.badge}`}
              >
                {BACKEND_TONE_LABELS[horizon.tone]}
              </span>
            </div>
            <SheetDescription className="sr-only">
              Разбор горизонта {horizon.eyebrow}
            </SheetDescription>
          </SheetHeader>

          {/* 2. Human meaning: summary + plainExplanation */}
          <div data-testid="why-horizon-meaning" className="space-y-2">
            <p className="text-[15px] font-semibold leading-relaxed text-foreground/90">{horizon.summary}</p>
            <p className="text-[15px] leading-relaxed text-muted-foreground">{horizon.plainExplanation}</p>
          </div>

          {/* 3. Timing */}
          <div data-testid="why-horizon-timing" className={`rounded-2xl border px-3 py-2.5 text-[13px] leading-relaxed text-foreground/85 ${toneStyle.timing}`}>
            {horizon.timing.rangeLabel ? <p data-testid="why-horizon-timing-range"><span className="font-semibold text-foreground">Период:</span> {horizon.timing.rangeLabel}</p> : null}
            {horizon.timing.peakLabel ? <p data-testid="why-horizon-timing-peak"><span className="font-semibold text-foreground">Пик:</span> {horizon.timing.peakLabel}</p> : null}
            <p data-testid="why-horizon-timing-state"><span className="font-semibold text-foreground">Сейчас:</span> {horizon.timing.stateLabel}</p>
          </div>

          {/* 4. Manifestations */}
          <div data-testid="why-horizon-manifestations" className="space-y-2">
            <p className="text-[12px] font-semibold text-foreground">Где это вероятнее проявится</p>
            <div className="space-y-2">
              {horizon.manifestations.map((item) => (
                <div key={item.id} className="rounded-2xl border border-border/60 bg-background/70 p-3">
                  <p className="text-[13px] font-semibold text-foreground">{item.title}</p>
                  {item.condition ? <p className="mt-1 text-[13px] leading-relaxed text-foreground/85">{item.condition}</p> : null}
                  <p className="mt-1 text-[14px] leading-relaxed text-muted-foreground">{item.body}</p>
                </div>
              ))}
            </div>
          </div>

          {/* 5. Patterns (strength/risk) */}
          <div data-testid="why-horizon-patterns" className="grid gap-3 sm:grid-cols-2">
            {horizon.strength ? (
              <div data-testid="why-horizon-strength" className="rounded-2xl border border-emerald-200/80 bg-emerald-50/50 p-3 dark:border-emerald-400/20 dark:bg-emerald-500/10">
                <p className="text-[12px] font-semibold text-foreground">На что можно опереться</p>
                <p className="mt-1 text-[14px] leading-relaxed text-foreground/85">{horizon.strength.text}</p>
              </div>
            ) : null}
            {horizon.risk ? (
              <div data-testid="why-horizon-risk" className="rounded-2xl border border-rose-200/80 bg-rose-50/55 p-3 dark:border-rose-400/20 dark:bg-rose-500/10">
                <p className="text-[12px] font-semibold text-foreground">Что может мешать</p>
                <p className="mt-1 text-[14px] leading-relaxed text-foreground/85">{horizon.risk.text}</p>
              </div>
            ) : null}
          </div>

          {/* 6. Actions */}
          <HorizonActions actions={horizon.actions} />

          {/* 7. Sphere links (opens sphere sheet and closes horizon sheet) */}
          {sphereRows.length ? (
            <div data-testid="why-horizon-spheres" className="space-y-2">
              <p className="text-[12px] font-semibold text-foreground">Открыть в навигаторе по 12 сферам</p>
              <div className="flex flex-wrap gap-2">
                {sphereRows.map((row) => (
                  <button
                    key={row.key}
                    type="button"
                    data-testid="why-horizon-sphere"
                    data-sphere-key={row.key}
                    onClick={() => {
                      onClose()
                      onSphereSelect?.(row.key)
                    }}
                    aria-label={`Открыть сферу «${row.label}» в навигаторе`}
                    className="min-h-11 rounded-full border border-violet-200 bg-violet-50 px-3.5 py-2 text-[13px] font-medium text-violet-800 transition hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 dark:border-violet-400/25 dark:bg-violet-500/10 dark:text-violet-100 active:scale-[0.985] cursor-pointer"
                  >
                    {row.label}
                  </button>
                ))}
              </div>
            </div>
          ) : null}

          {/* 8. Technique disclosure */}
          <HorizonTechniqueDisclosure explanations={horizon.techniqueExplanations} horizon={horizon.horizon} />

          {/* Close button */}
          <div className="pt-2 pb-2">
            <button
              type="button"
              onClick={onClose}
              className="w-full min-h-12 rounded-2xl border border-border/60 bg-muted/30 px-5 text-[14.5px] font-medium text-muted-foreground transition hover:text-foreground active:scale-[0.985] cursor-pointer flex items-center justify-center"
            >
              Закрыть
            </button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
// END_BLOCK: HORIZON_SHEET_RENDER
