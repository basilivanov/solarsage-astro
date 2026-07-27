// ############################################################################
// AI_HEADER: MODULE_TODAY_SPHERE_DETAILS_SHEET
// ROLE: BottomSheet modal component for human-first sphere drilldown details.
// DEPENDENCIES: react, components/ui/sheet, lib/contracts/today, lib/icons, lib/presentation/today-v2.
// GRACE_ANCHORS: [SPHERE_DETAILS_SHEET]
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-SPHERE-DETAILS-SHEET
// purpose: Render a instant bottom-sheet modal for one selected sphere row from payload.
// owns:
//   - components/today/sphere-details-sheet.tsx
// inputs: row (ConcreteAdviceRow | null), onClose (function), onWhyOpen (function).
// outputs: Sheet modal with data-testid="sphere-details-sheet".
// dependencies: components/ui/sheet, lib/contracts/today, lib/icons.
// side_effects: opens/closes Radix Sheet modal, delegates Why navigation to parent.
// emitted_logs: none.
// failure_policy: renders fallback advice text when details object is missing.
// END_MODULE_CONTRACT: M-TODAY-SPHERE-DETAILS-SHEET

// START_MODULE_MAP: M-TODAY-SPHERE-DETAILS-SHEET
// public_entrypoints:
//   - SphereDetailsSheet
// semantic_blocks:
//   - SPHERE_SHEET_RENDER: render Radix Sheet bottom modal with story, why, and advice details.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
//   - __tests__/components/TodayScreen.test.tsx
// END_MODULE_MAP: M-TODAY-SPHERE-DETAILS-SHEET

"use client"

import React from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import type { ConcreteAdviceRow } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"
import { getHumanSphereLabel } from "@/lib/presentation/today-v2"

interface SphereDetailsSheetProps {
  row: ConcreteAdviceRow | null
  onClose: () => void
  onWhyOpen: () => void
}

// START_BLOCK: SPHERE_SHEET_RENDER
export function SphereDetailsSheet({ row, onClose, onWhyOpen }: SphereDetailsSheetProps) {
  const isOpen = Boolean(row)

  if (!row) return null

  const Icon = getIcon(row.iconName)
  const label = getHumanSphereLabel(row)
  const details = row.details ?? null

  const storyText = details?.story?.trim() || null
  const whyItems = (details?.why || []).filter((w) => Boolean(w && w.trim()))
  const adviceText = details?.advice?.trim() || row.text

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="bottom"
        data-testid="sphere-details-sheet"
        data-sphere-key={row.key}
        className="rounded-t-[24px] border-t border-border/60 bg-card max-h-[85dvh] flex flex-col p-0 outline-none"
      >
        {/* Grabber bar */}
        <div className="w-12 h-1 bg-border/80 rounded-full mx-auto mt-3 mb-1 flex-none" aria-hidden="true" />

        <div className="overflow-y-auto px-6 py-4 space-y-5 flex-1">
          <SheetHeader className="p-0 space-y-0">
            <div className="flex items-center gap-3.5">
              <span className="flex h-11 w-11 flex-none items-center justify-center rounded-2xl bg-violet-100/70 text-violet-700 dark:bg-violet-500/15 dark:text-violet-200">
                <Icon className="h-5 w-5" strokeWidth={1.8} aria-hidden="true" />
              </span>
              <SheetTitle className="font-serif text-[24px] font-semibold leading-tight text-foreground m-0">
                {label}
              </SheetTitle>
            </div>
            <SheetDescription className="sr-only">
              Персональный разбор сферы {label}
            </SheetDescription>
          </SheetHeader>

          {/* 2. Story (2-3 sentences about the person and their day) */}
          {storyText ? (
            <p className="text-[15px] leading-relaxed text-foreground">
              {storyText}
            </p>
          ) : null}

          {/* 3. Section "Что за этим стоит" (why background factors) */}
          {whyItems.length > 0 ? (
            <div className="space-y-2 pt-1 border-t border-border/40">
              <h4 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-200">
                Что за этим стоит
              </h4>
              <ul className="space-y-2 pl-0 list-none">
                {whyItems.map((item, idx) => (
                  <li key={idx} className="flex items-start gap-2.5 text-[14.5px] leading-relaxed text-muted-foreground">
                    <span className="h-1.5 w-1.5 rounded-full bg-violet-400 flex-none mt-2" aria-hidden="true" />
                    <span>{item}</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {/* 4. Section "Что поможет" (advice) */}
          <div className="space-y-1.5 pt-1 border-t border-border/40">
            <h4 className="text-[13px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-200">
              Что поможет
            </h4>
            <p className="text-[15px] leading-relaxed text-foreground font-medium">
              {adviceText}
            </p>
          </div>

          {/* 5. Action CTAs */}
          <div className="pt-3 pb-2 flex flex-wrap gap-2.5">
            <button
              type="button"
              data-testid="sphere-why-cta"
              onClick={() => {
                onClose()
                onWhyOpen()
              }}
              className="flex-1 min-h-12 rounded-2xl border border-violet-300 bg-violet-50/80 px-4 text-[14.5px] font-semibold text-violet-800 transition hover:bg-violet-100 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 dark:border-violet-400/40 dark:bg-violet-500/15 dark:text-violet-100 active:scale-[0.985] cursor-pointer text-center justify-center flex items-center"
            >
              Почему так у меня
            </button>
            <button
              type="button"
              onClick={onClose}
              className="min-h-12 rounded-2xl border border-border/60 bg-muted/30 px-5 text-[14.5px] font-medium text-muted-foreground transition hover:text-foreground active:scale-[0.985] cursor-pointer flex items-center justify-center"
            >
              Закрыть
            </button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  )
}
// END_BLOCK: SPHERE_SHEET_RENDER
