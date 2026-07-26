// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_ASPECT_DRILLDOWN_SHEET
// ROLE: Aspect drill-down detail modal sheet for synastry
// DEPENDENCIES: react, lucide-react, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET
// purpose: Render structured aspect drilldown sheet modal with planet cards, aspect mechanics, life scenes, repairs, and not-means.
// owns:
//   - components/synastry/aspect-drilldown-sheet.tsx
// inputs: open, aspectId, partnerId, onClose
// outputs: AspectDrilldownSheet TSX render
// dependencies: lib/api/synastry, components/synastry/synastry-tone
// side_effects: fetches aspect drilldown data when opened
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET

// START_MODULE_MAP: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET
// public_entrypoints:
//   - AspectDrilldownSheet
// semantic_blocks:
//   - ASPECT_DRILLDOWN_SHEET: Drill-down modal component
// owned_tests:
//   - __tests__/synastry/aspect-drilldown-sheet.test.tsx
// END_MODULE_MAP: M-SYNASTRY-ASPECT-DRILLDOWN-SHEET

"use client"

import { useEffect, useState } from "react"
import { X, Sparkles, AlertCircle, CheckCircle2, ShieldAlert, BookOpen } from "lucide-react"
import { getAspectDrilldown, type AspectDrilldownData } from "@/lib/api/synastry"
import { getToneStatusLabel, normalizeSynastryTone } from "./synastry-tone"

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

  const tone = normalizeSynastryTone(data?.tone)
  const symbol = data?.aspectSymbol || "△"
  const kindLabel = data?.aspectKindLabel || "Аспект"
  const orbStr = data?.orbText || ""
  // Localized tech signature ("Меркурий □ Меркурий") — never show the raw English engine signature.
  const techLine =
    data?.ownerPlanet && data?.partnerPlanet
      ? `${data.ownerPlanet.label} ${symbol} ${data.partnerPlanet.label}`
      : data?.techSignature || data?.title || ""

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aspect-drilldown-title"
      data-testid="aspect-drilldown-sheet"
      data-tone={tone}
    >
      <div className="relative w-full max-w-lg max-h-[90dvh] flex flex-col rounded-t-[28px] sm:rounded-[28px] border border-border/70 bg-background p-6 shadow-2xl space-y-5 overflow-hidden">
        {/* Grabber bar */}
        <div className="mx-auto h-1.5 w-12 rounded-full bg-muted-foreground/30 flex-none" />

        {/* Header */}
        <div className="flex items-start justify-between gap-4 border-b border-border/40 pb-3 flex-none">
          <div>
            <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
              АСТРОЛОГИЧЕСКИЙ КОНТАКТ
            </span>
            <h2 id="aspect-drilldown-title" className="font-serif text-[22px] font-semibold text-foreground leading-tight">
              {data?.headline || data?.title || aspectId}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-card border border-border/70 text-muted-foreground transition hover:text-foreground active:scale-95"
          >
            <X className="h-5 w-5" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto space-y-6 pr-1">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3" role="status" aria-busy="true">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-primary border-t-transparent" />
              <span className="text-[13px] text-muted-foreground">Готовим подробный разбор…</span>
            </div>
          ) : error ? (
            <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-4 text-center space-y-2" role="alert">
              <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
              <p className="text-[13px] text-destructive">{error}</p>
            </div>
          ) : data ? (
            <div className="space-y-6 text-[14px] leading-relaxed text-foreground/85">
              {/* 1. Hero Summary Card */}
              <div className="flex items-center gap-4 rounded-[20px] border border-border/70 bg-card p-4 shadow-sm">
                <div
                  className={`flex h-[50px] w-[50px] flex-none items-center justify-center rounded-[16px] text-[22px] font-bold ${
                    tone === "good"
                      ? "bg-[#eaf5f0] text-[#43806d] dark:bg-[#1c2b25] dark:text-[#63a893]"
                      : tone === "bad"
                      ? "bg-[#fae9ec] text-[#a64d59] dark:bg-[#2d1c20] dark:text-[#c96b77]"
                      : "bg-[#fbf1de] text-[#b07b36] dark:bg-[#2d261a] dark:text-[#d49a4f]"
                  }`}
                >
                  {symbol}
                </div>
                <div className="min-w-0 flex-1 space-y-0.5">
                  <div className="text-[14.5px] font-bold text-foreground truncate">
                    {techLine}
                  </div>
                  <div className="text-[12px] text-muted-foreground">
                    {kindLabel} {orbStr ? `· ${orbStr}` : ""} · {getToneStatusLabel(tone).toLowerCase()}
                  </div>
                </div>
              </div>

              {/* 2. What connects (Two Planet Cards) */}
              {(data.ownerPlanet || data.partnerPlanet) && (
                <div className="space-y-2">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground">
                    Что именно соединяется
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.ownerPlanet && (
                      <div className="rounded-[18px] bg-[#f1e9f4]/70 dark:bg-[#2d2233]/70 p-4 space-y-2">
                        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-primary">
                          ТВОЯ КАРТА
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="font-serif font-bold text-[18px] text-primary">
                            {data.ownerPlanet.glyph}
                          </span>
                          <span className="font-serif font-semibold text-[16px] text-foreground">
                            {data.ownerPlanet.label}
                          </span>
                        </div>
                        <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                          {data.ownerPlanet.meaning}
                        </p>
                      </div>
                    )}

                    {data.partnerPlanet && (
                      <div className="rounded-[18px] bg-[#fbf1de]/70 dark:bg-[#2d261a]/70 p-4 space-y-2">
                        <span className="text-[10px] font-bold uppercase tracking-[0.14em] text-[#b07b36] dark:text-[#d49a4f]">
                          КАРТА ПАРТНЁРА
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="font-serif font-bold text-[18px] text-[#b07b36] dark:text-[#d49a4f]">
                            {data.partnerPlanet.glyph}
                          </span>
                          <span className="font-serif font-semibold text-[16px] text-foreground">
                            {data.partnerPlanet.label}
                          </span>
                        </div>
                        <p className="text-[12.5px] leading-relaxed text-muted-foreground">
                          {data.partnerPlanet.meaning}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Aspect Mechanics */}
              {data.aspectMechanics && (
                <div className="space-y-1.5">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <BookOpen className="h-3.5 w-3.5 text-primary" />
                    Как работает {kindLabel.toLowerCase()}
                  </h3>
                  <div className="rounded-[18px] border border-border/70 bg-card p-4 text-[13.5px] leading-relaxed text-foreground/85">
                    {data.aspectMechanics}
                  </div>
                </div>
              )}

              {/* Explanation / Deep psychological dynamic */}
              {data.explanation && (
                <div className="rounded-[18px] border border-primary/15 bg-primary/[0.03] p-4 text-[14px] leading-relaxed font-serif">
                  {data.explanation}
                </div>
              )}

              {/* 4. Life Scenes */}
              {data.scenes && data.scenes.length > 0 ? (
                <div className="space-y-2.5">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    Как это проявляется в жизни
                  </h3>
                  <div className="space-y-2">
                    {data.scenes.map((scene, idx) => (
                      <div key={idx} className="rounded-[16px] border border-border/60 bg-card p-3.5 space-y-1">
                        <div className="text-[13px] font-semibold text-foreground">{scene.title}</div>
                        <div className="text-[12.5px] text-muted-foreground leading-relaxed">{scene.text}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : data.scenario ? (
                <div className="space-y-2">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <Sparkles className="h-3.5 w-3.5 text-primary" />
                    Как это проявляется в жизни
                  </h3>
                  <div className="rounded-[18px] border border-border/70 bg-card p-4 text-[13.5px] leading-relaxed text-muted-foreground">
                    {data.scenario}
                  </div>
                </div>
              ) : null}

              {/* 5. Repairs / What helps */}
              {data.repairs && data.repairs.length > 0 ? (
                <div className="space-y-2.5">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-[#43806d]" />
                    Что помогает и гармонизирует
                  </h3>
                  <div className="space-y-2">
                    {data.repairs.map((repair, idx) => (
                      <div
                        key={idx}
                        className="flex items-start gap-3 rounded-[16px] bg-[#eaf5f0] dark:bg-[#1c2b25] p-3.5 text-[13px] leading-relaxed text-[#43806d] dark:text-[#63a893]"
                      >
                        <span className="flex h-5 w-5 flex-none items-center justify-center rounded-full bg-[#43806d] text-white text-[11px] font-bold">
                          {idx + 1}
                        </span>
                        <div className="flex-1">{repair}</div>
                      </div>
                    ))}
                  </div>
                </div>
              ) : data.advice ? (
                <div className="space-y-2">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <CheckCircle2 className="h-3.5 w-3.5 text-[#43806d]" />
                    Что помогает
                  </h3>
                  <div className="rounded-[18px] bg-[#eaf5f0] dark:bg-[#1c2b25] p-4 text-[13.5px] leading-relaxed text-[#43806d] dark:text-[#63a893]">
                    {data.advice}
                  </div>
                </div>
              ) : null}

              {/* 6. Not means / Protection from fatalism */}
              {data.notMeans && data.notMeans.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-border/40">
                  <h3 className="text-[11px] font-semibold uppercase tracking-[0.14em] text-muted-foreground flex items-center gap-1.5">
                    <ShieldAlert className="h-3.5 w-3.5 text-[#b07b36]" />
                    Важно: это НЕ означает
                  </h3>
                  <div className="space-y-2">
                    {data.notMeans.map((item, idx) => (
                      <div
                        key={idx}
                        className="rounded-[14px] bg-[#fbf1de]/60 dark:bg-[#2d261a]/60 px-3.5 py-2.5 text-[12.5px] text-[#b07b36] dark:text-[#d49a4f] leading-relaxed"
                      >
                        • {item}
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer CTA */}
        <button
          type="button"
          onClick={onClose}
          className="w-full h-12 rounded-[18px] bg-[#3e3347] dark:bg-[#f1e9f4] text-[#fffdf9] dark:text-[#3e3347] text-[14.5px] font-semibold transition active:scale-[0.99] flex-none"
        >
          Понятно
        </button>
      </div>
    </div>
  )
}
// END_BLOCK: ASPECT_DRILLDOWN_SHEET
