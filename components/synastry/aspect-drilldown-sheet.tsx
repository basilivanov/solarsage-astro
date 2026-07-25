// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_ASPECT_DRILLDOWN_SHEET
// ROLE: Aspect drill-down detail modal sheet for synastry
// DEPENDENCIES: react, lucide-react, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET
// purpose: Render aspect drilldown sheet modal with planet functions, aspect mechanics, life scenes, and repairs.
// owns:
//   - components/synastry/aspect-drilldown-sheet.tsx
// inputs: open, aspectId, partnerId, onClose
// outputs: AspectDrilldownSheet TSX render
// dependencies: lib/api/synastry
// side_effects: fetches aspect drilldown data when opened
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET

// START_MODULE_MAP: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET
// public_entrypoints:
//   - AspectDrilldownSheet
// semantic_blocks:
//   - ASPECT_DRILLDOWN_SHEET: Drill-down modal component
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET

"use client"

import { useEffect, useState } from "react"
import { X, Sparkles, AlertCircle, CheckCircle2, ShieldAlert } from "lucide-react"
import { getAspectDrilldown, type AspectDrilldownData } from "@/lib/api/synastry"

type Props = {
  open: boolean
  partnerId: string | null
  aspectId: string | null
  onClose: () => void
}

// START_BLOCK: ASPECT_DRILLDOWN_SHEET
export function AspectDrilldownSheet({ open, partnerId, aspectId, onClose }: Props) {
  const [data, setData] = useState<AspectDrilldownData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open || !partnerId || !aspectId) {
      setData(null)
      setError(null)
      return
    }

    let active = true
    setLoading(true)
    setError(null)

    getAspectDrilldown(partnerId, aspectId)
      .then((res) => {
        if (!active) return
        setData(res)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : "Failed to load aspect drilldown")
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
    }
  }, [open, partnerId, aspectId])

  if (!open) return null

  const tone = data?.tone || "mixed"

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aspect-drilldown-title"
      data-testid="aspect-drilldown-sheet"
      data-tone={tone}
    >
      <div className="relative w-full max-w-lg max-h-[90vh] overflow-y-auto rounded-t-3xl sm:rounded-3xl border border-border/70 bg-card p-6 shadow-2xl space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-border/50 pb-4">
          <div>
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              {data?.techSignature || "Детали аспекта"}
            </span>
            <h2 id="aspect-drilldown-title" className="font-serif text-[22px] font-semibold text-foreground">
              {data?.title || aspectId}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-muted/60 text-muted-foreground transition hover:text-foreground active:scale-95"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Content */}
        {loading ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3" role="status" aria-busy="true">
            <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
            <span className="text-[13px] text-muted-foreground">Готовим подробный разбор…</span>
          </div>
        ) : error ? (
          <div className="rounded-2xl border border-destructive/20 bg-destructive/5 p-4 text-center space-y-2" role="alert">
            <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
            <p className="text-[13px] text-destructive">{error}</p>
          </div>
        ) : data ? (
          <div className="space-y-6 text-[14px] leading-relaxed text-foreground/85">
            {/* Explanation / Intro */}
            <div className="rounded-2xl border border-primary/15 bg-primary/[0.03] p-4 font-serif text-[15px] leading-relaxed">
              {data.explanation}
            </div>

            {/* Life Scenes */}
            {data.scenario && (
              <div className="space-y-2">
                <h3 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-muted-foreground flex items-center gap-1.5">
                  <Sparkles className="h-3.5 w-3.5 text-primary" />
                  Как проявляется в жизни
                </h3>
                <div className="rounded-2xl border border-border/70 bg-background/60 p-4 text-[13.5px] leading-relaxed">
                  {data.scenario}
                </div>
              </div>
            )}

            {/* What helps / Advice */}
            {data.advice && (
              <div className="space-y-2">
                <h3 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-muted-foreground flex items-center gap-1.5">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  Что помогает и гармонизирует
                </h3>
                <div className="rounded-2xl border border-emerald-500/20 bg-emerald-500/5 p-4 text-[13.5px] leading-relaxed text-emerald-950 dark:text-emerald-100">
                  {data.advice}
                </div>
              </div>
            )}

            {/* Protection against fatalism */}
            <div className="space-y-2 pt-2 border-t border-border/40">
              <h3 className="text-[12px] font-semibold uppercase tracking-[0.12em] text-muted-foreground flex items-center gap-1.5">
                <ShieldAlert className="h-3.5 w-3.5 text-amber-500" />
                Это НЕ означает
              </h3>
              <ul className="space-y-2 text-[12.5px] text-muted-foreground">
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span>Что вы не сможете договориться или прийти к согласию.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span>Что кто-то в паре поступает так намеренно или со злым умыслом.</span>
                </li>
                <li className="flex items-start gap-2">
                  <span className="text-amber-500">•</span>
                  <span>Что этот напряжённый контакт выносит приговор вашим отношениям.</span>
                </li>
              </ul>
            </div>
          </div>
        ) : null}

        {/* Footer */}
        <button
          type="button"
          onClick={onClose}
          className="w-full rounded-2xl bg-muted py-3 text-[14px] font-medium text-foreground transition active:scale-[0.99]"
        >
          Понятно
        </button>
      </div>
    </div>
  )
}
// END_BLOCK: ASPECT_DRILLDOWN_SHEET
