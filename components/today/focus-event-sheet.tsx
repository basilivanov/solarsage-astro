// ############################################################################
// AI_HEADER: MODULE_TODAY_FOCUS_EVENT_SHEET
// ROLE: BottomSheet modal component for lazy-loaded focus event drilldown.
// DEPENDENCIES: react, components/ui/sheet, lib/contracts/today, lucide-react
// GRACE_ANCHORS: [FOCUS_EVENT_SHEET]
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-FOCUS-EVENT-SHEET
// purpose: Render a bottom-sheet modal lazy-loading FocusEventDrilldown for a selected focus event (§47-72 of E2 TZ).
// owns:
//   - components/today/focus-event-sheet.tsx
// inputs: date (string), event (TodayFocusEvent | null), onClose (function)
// outputs: Sheet modal with data-testid="focus-event-sheet"
// dependencies: components/ui/sheet, lib/contracts/today, lucide-react
// side_effects: fetches GET /api/day/{date}/focus-event/{event_id} on demand, caches responses
// emitted_logs: none
// failure_policy: handles loading and HTTP error states with accessible retry button
// END_MODULE_CONTRACT: M-TODAY-FOCUS-EVENT-SHEET

// START_MODULE_MAP: M-TODAY-FOCUS-EVENT-SHEET
// public_entrypoints:
//   - FocusEventSheet
// semantic_blocks:
//   - EVENT_SHEET_RENDER: render Radix Sheet bottom modal with lazy fetch, caching, skeleton, error, and ready sections
// owned_tests:
//   - __tests__/components/FocusEventSheet.test.tsx
// END_MODULE_MAP: M-TODAY-FOCUS-EVENT-SHEET

"use client"

import React, { useEffect, useRef, useState } from "react"
import { ArrowDown, RefreshCw } from "lucide-react"
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from "@/components/ui/sheet"
import type { TodayFocusEvent, FocusEventDrilldown } from "@/lib/contracts/today"

interface FocusEventSheetProps {
  date: string
  event: TodayFocusEvent | null
  onClose: () => void
}

// START_BLOCK: EVENT_SHEET_RENDER
export function FocusEventSheet({ date, event, onClose }: FocusEventSheetProps) {
  const isOpen = Boolean(event)
  const cacheRef = useRef<Map<string, FocusEventDrilldown>>(new Map())

  const [drilldown, setDrilldown] = useState<FocusEventDrilldown | null>(null)
  const [loading, setLoading] = useState<boolean>(false)
  const [error, setError] = useState<boolean>(false)

  const eventId = event?.id

  const loadDrilldown = async (targetEventId: string, abortSignal?: AbortSignal) => {
    if (cacheRef.current.has(targetEventId)) {
      setDrilldown(cacheRef.current.get(targetEventId)!)
      setLoading(false)
      setError(false)
      return
    }

    setLoading(true)
    setError(false)
    setDrilldown(null)

    try {
      const encodedId = encodeURIComponent(targetEventId)
      const res = await fetch(`/api/day/${date}/focus-event/${encodedId}`, {
        credentials: "include",
        signal: abortSignal,
      })

      if (!res.ok) {
        throw new Error(`HTTP ${res.status}`)
      }

      const data: FocusEventDrilldown = await res.json()
      cacheRef.current.set(targetEventId, data)
      setDrilldown(data)
      setLoading(false)
    } catch (err: any) {
      if (err?.name === "AbortError") return
      setError(true)
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!eventId) {
      setDrilldown(null)
      setLoading(false)
      setError(false)
      return
    }

    const controller = new AbortController()
    loadDrilldown(eventId, controller.signal)

    return () => {
      controller.abort()
    }
  }, [eventId, date])

  if (!event) return null

  const dataState = loading ? "loading" : error ? "error" : "ready"

  return (
    <Sheet open={isOpen} onOpenChange={(open) => { if (!open) onClose() }}>
      <SheetContent
        side="bottom"
        data-testid="focus-event-sheet"
        data-state={dataState}
        data-event-id={event.id}
        className="rounded-t-[24px] border-t border-border/60 bg-card max-h-[88dvh] flex flex-col p-0 outline-none max-w-md mx-auto"
      >
        {/* Grabber bar */}
        <div className="w-12 h-1 bg-border/80 rounded-full mx-auto mt-3 mb-1 flex-none" aria-hidden="true" />

        <SheetHeader className="sr-only">
          <SheetTitle>{drilldown?.humanTitle || event.humanTitle || "Разбор события"}</SheetTitle>
          <SheetDescription>Детальный разбор события</SheetDescription>
        </SheetHeader>

        <div className="overflow-y-auto px-6 py-4 space-y-5 flex-1">
          {/* Loading state skeleton */}
          {loading && (
            <div role="status" aria-busy="true" className="space-y-4 pt-2">
              <div className="h-6 w-3/4 bg-muted rounded animate-pulse" />
              <div className="h-4 w-1/3 bg-muted rounded animate-pulse" />
              <div className="space-y-2 pt-3">
                <div className="h-16 bg-muted rounded-2xl animate-pulse" />
                <div className="h-16 bg-muted rounded-2xl animate-pulse" />
              </div>
              <span className="sr-only">Загрузка разбора события…</span>
            </div>
          )}

          {/* Error state */}
          {error && (
            <div role="alert" className="space-y-3 py-6 text-center">
              <p className="text-[14.5px] font-medium text-foreground">
                Не удалось загрузить разбор события
              </p>
              <button
                type="button"
                data-testid="focus-event-retry"
                onClick={() => loadDrilldown(event.id)}
                className="inline-flex items-center gap-1.5 px-4 py-2 text-[13.5px] font-semibold text-violet-700 dark:text-violet-300 bg-violet-100/80 dark:bg-violet-500/20 rounded-xl transition hover:bg-violet-200 cursor-pointer"
              >
                <RefreshCw className="h-4 w-4" aria-hidden="true" />
                Повторить
              </button>
            </div>
          )}

          {/* Ready state content */}
          {!loading && !error && drilldown && (
            <>
              {/* 1. Header */}
              <div className="p-0 space-y-1.5 text-left">
                <h3 data-testid="focus-event-title" className="font-serif text-[22px] font-semibold leading-tight text-foreground m-0">
                  {drilldown.humanTitle}
                </h3>
                <div data-testid="focus-event-kind" className="flex items-center gap-2">
                  <span className="inline-flex items-center rounded-full bg-violet-100 px-2.5 py-0.5 text-[12px] font-semibold text-violet-700 dark:bg-violet-500/20 dark:text-violet-200">
                    {drilldown.kindLabel}{drilldown.localTime ? ` · ${drilldown.localTime}` : ""}
                  </span>
                </div>
              </div>

              {/* 2. Source & Target sides ("Что именно взаимодействует") */}
              {(drilldown.source || drilldown.target) && (
                <div data-testid="focus-event-planets" className="space-y-2 pt-2 border-t border-border/40">
                  <h4 className="text-[12.5px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-300">
                    Что именно взаимодействует
                  </h4>
                  <div className="space-y-2">
                    {drilldown.source && (
                      <div className="p-3 rounded-2xl border border-border/60 bg-muted/20 space-y-1">
                        <div className="flex items-center justify-between text-[13px] font-semibold text-foreground">
                          <span>{drilldown.source.label}</span>
                          <span className="text-[11px] text-muted-foreground font-normal">
                            {drilldown.source.frameLabel}
                          </span>
                        </div>
                        <p className="text-[13px] text-muted-foreground">
                          {drilldown.source.functionText}
                        </p>
                      </div>
                    )}

                    {drilldown.source && drilldown.target && (
                      <div className="flex justify-center py-0.5 text-violet-500">
                        <ArrowDown className="h-4 w-4" aria-hidden="true" />
                      </div>
                    )}

                    {drilldown.target && (
                      <div className="p-3 rounded-2xl border border-border/60 bg-muted/20 space-y-1">
                        <div className="flex items-center justify-between text-[13px] font-semibold text-foreground">
                          <span>{drilldown.target.label}</span>
                          <span className="text-[11px] text-muted-foreground font-normal">
                            {drilldown.target.frameLabel}
                          </span>
                        </div>
                        <p className="text-[13px] text-muted-foreground">
                          {drilldown.target.functionText}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Aspect mechanics */}
              {(drilldown.aspectLabel || drilldown.aspectMechanics) && (
                <div data-testid="focus-event-mechanics" className="space-y-1.5 pt-2 border-t border-border/40">
                  <h4 className="text-[12.5px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-300">
                    Как работает {drilldown.aspectLabel || "взаимодействие"}
                  </h4>
                  <div className="flex items-start gap-2.5">
                    {drilldown.aspectSymbol && (
                      <span className="text-[18px] font-bold text-violet-600 dark:text-violet-400 flex-none leading-none mt-0.5">
                        {drilldown.aspectSymbol}
                      </span>
                    )}
                    {drilldown.aspectMechanics && (
                      <p className="text-[14px] leading-relaxed text-muted-foreground">
                        {drilldown.aspectMechanics}
                      </p>
                    )}
                  </div>
                </div>
              )}

              {/* 4. Meaning */}
              {drilldown.meaning && (
                <div data-testid="focus-event-meaning" className="space-y-1.5 pt-2 border-t border-border/40">
                  <h4 className="text-[12.5px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-300">
                    Что это значит сегодня
                  </h4>
                  <p className="text-[14.5px] leading-relaxed text-foreground font-medium">
                    {drilldown.meaning}
                  </p>
                </div>
              )}

              {/* 5. Numbers (definition list) */}
              {(drilldown.numbers?.length ?? 0) > 0 && (
                <div data-testid="focus-event-numbers" className="space-y-2 pt-2 border-t border-border/40">
                  <h4 className="text-[12.5px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-300">
                    Точные цифры
                  </h4>
                  <dl className="grid grid-cols-2 gap-2 text-[13px]">
                    {(drilldown.numbers ?? []).map((num, idx) => (
                      <div key={idx} className="p-2.5 rounded-xl bg-muted/30 border border-border/40">
                        <dt className="text-muted-foreground text-[11.5px] font-medium">{num.label}</dt>
                        <dd className="font-mono font-semibold text-foreground mt-0.5">{num.value}</dd>
                      </div>
                    ))}
                  </dl>
                </div>
              )}

              {/* 6. Footer technique label */}
              {drilldown.techniqueLabel && (
                <div data-testid="focus-event-technique" className="pt-2 border-t border-border/30 text-center">
                  <p className="text-[11.5px] text-muted-foreground">
                    {drilldown.techniqueLabel}
                  </p>
                </div>
              )}
            </>
          )}
        </div>
      </SheetContent>
    </Sheet>
  )
}
// END_BLOCK: EVENT_SHEET_RENDER
