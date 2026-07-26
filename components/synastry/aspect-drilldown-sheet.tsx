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
import { X, AlertCircle } from "lucide-react"
import { getAspectDrilldown, SynastryApiError, type AspectDrilldownData } from "@/lib/api/synastry"
import { getToneContactLabel, normalizeSynastryTone } from "./synastry-tone"

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

  // Escape closes the sheet (accessibility contract)
  useEffect(() => {
    if (!open) return
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose()
    }
    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [open, onClose])

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
        // User-facing copy is always Russian; technical details stay in logs.
        if (err instanceof SynastryApiError && err.code && err.code !== err.message) {
          setError(err.message)
        } else {
          setError("Не удалось загрузить разбор аспекта. Попробуйте ещё раз.")
        }
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
  const techLine =
    data?.ownerPlanet && data?.partnerPlanet
      ? `${data.ownerPlanet.label} ${symbol} ${data.partnerPlanet.label}`
      : data?.techSignature || data?.title || aspectId || ""
  const headline = data?.headline || data?.title || aspectId || ""

  return (
    <div
      className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-[rgba(44,35,48,0.35)] p-0 sm:p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="aspect-drilldown-title"
      data-testid="aspect-drilldown-sheet"
      data-tone={tone}
    >
      <div className="relative w-full max-w-lg max-h-[90dvh] flex flex-col rounded-t-[28px] sm:rounded-[28px] bg-[#fbf8f2] dark:bg-[#201826] p-6 shadow-2xl space-y-4 overflow-hidden">
        {/* Grabber bar */}
        <div className="mx-auto h-1.5 w-12 rounded-full bg-[#7d7284]/30 flex-none sm:hidden" />

        {/* Header: Eyebrow + H2 Tech Signature (exact macro layout) */}
        <div className="flex items-start justify-between gap-4 border-b border-[#e8e0e8] pb-3 flex-none">
          <div>
            <span className="text-[11px] font-extrabold uppercase tracking-[0.14em] text-[#795a86]">
              АСТРОЛОГИЧЕСКИЙ КОНТАКТ
            </span>
            <h2 id="aspect-drilldown-title" className="syn-serif text-[22px] font-medium text-[#3e3347] dark:text-[#f1e9f4] leading-tight">
              {techLine}
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Закрыть"
            className="flex h-8 w-8 flex-none items-center justify-center rounded-full bg-[#f1e9f4] text-[#3e3347] hover:bg-[#e8e0e8] transition active:scale-95"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* Scrollable Body */}
        <div className="flex-1 overflow-y-auto space-y-5 pr-1">
          {loading ? (
            <div className="flex flex-col items-center justify-center py-12 gap-3" role="status" aria-busy="true">
              <div className="h-7 w-7 animate-spin rounded-full border-2 border-[#795a86] border-t-transparent" />
              <span className="text-[13px] text-[#7d7284]">Готовим подробный разбор…</span>
            </div>
          ) : error ? (
            <div className="rounded-[14px] border border-destructive/20 bg-destructive/10 p-4 text-center space-y-2" role="alert">
              <AlertCircle className="mx-auto h-6 w-6 text-destructive" />
              <p className="text-[13px] text-destructive">{error}</p>
            </div>
          ) : data ? (
            <div className="space-y-5 text-[14px] leading-relaxed">
              {/* 1. Hero Summary Card: Tone square + Headline + Meta line (exact macro layout) */}
              <div className="flex items-center gap-[13px] rounded-[20px] bg-gradient-to-br from-[#f6eef8] to-[#fff8f1] dark:from-[#2a1d2e] dark:to-[#2e241e] p-[14px]">
                <div
                  className={`flex h-[50px] w-[50px] flex-none items-center justify-center rounded-[17px] text-[27px] font-[850] ${
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
                  <h3 className="font-sans text-[18px] font-bold text-[#3e3347] dark:text-[#f1e9f4] m-0 leading-tight">
                    {headline}
                  </h3>
                  <div className="text-[11px] text-[#7d7284] dark:text-muted-foreground">
                    {kindLabel} {orbStr ? `· ${orbStr}` : ""} · {getToneContactLabel(tone)}
                  </div>
                </div>
              </div>

              {/* 2. What connects (Two Planet Cards .planet-meaning) */}
              {(data.ownerPlanet || data.partnerPlanet) && (
                <div className="space-y-2">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    ЧТО ИМЕННО СОЕДИНЯЕТСЯ
                  </h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                    {data.ownerPlanet && (
                      <div className="rounded-[17px] bg-[#f7f2f7] dark:bg-[#2d2233] p-[13px] space-y-1">
                        <span className="block font-sans text-[9px] font-[850] uppercase tracking-wider text-[#795a86]">
                          ТВОЯ КАРТА
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="syn-serif text-[16px] text-[#3e3347] dark:text-[#f1e9f4]">
                            {data.ownerPlanet.glyph}
                          </span>
                          <strong className="text-[14px] font-bold text-[#3e3347] dark:text-[#f1e9f4]">
                            {data.ownerPlanet.label}
                          </strong>
                        </div>
                        <p className="text-[11.5px] leading-[1.42] text-[#65596a] dark:text-muted-foreground m-0">
                          {data.ownerPlanet.meaning}
                        </p>
                      </div>
                    )}

                    {data.partnerPlanet && (
                      <div className="rounded-[17px] bg-[#fbf3ed] dark:bg-[#2d261a] p-[13px] space-y-1">
                        <span className="block font-sans text-[9px] font-[850] uppercase tracking-wider text-[#b07b36]">
                          КАРТА ПАРТНЁРА
                        </span>
                        <div className="flex items-center gap-2">
                          <span className="syn-serif text-[16px] text-[#3e3347] dark:text-[#f1e9f4]">
                            {data.partnerPlanet.glyph}
                          </span>
                          <strong className="text-[14px] font-bold text-[#3e3347] dark:text-[#f1e9f4]">
                            {data.partnerPlanet.label}
                          </strong>
                        </div>
                        <p className="text-[11.5px] leading-[1.42] text-[#65596a] dark:text-muted-foreground m-0">
                          {data.partnerPlanet.meaning}
                        </p>
                      </div>
                    )}
                  </div>
                </div>
              )}

              {/* 3. Aspect Mechanics (.meaning-card) */}
              {data.aspectMechanics && (
                <div className="space-y-1.5">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    КАК РАБОТАЕТ {kindLabel.toUpperCase()}
                  </h3>
                  <div className="rounded-[17px] border border-[#e8e0e8] bg-white dark:bg-[#2d2233] p-[13px] space-y-1">
                    <p className="text-[12.5px] leading-[1.5] text-[#5e5262] dark:text-[#d4c8db] m-0">
                      {data.aspectMechanics}
                    </p>
                  </div>
                </div>
              )}

              {/* Explanation / Deep psychological dynamic */}
              {data.explanation && (
                <div className="rounded-[17px] border border-[#795a86]/20 bg-[#f7f2f7]/50 dark:bg-[#2a1d2e]/50 p-[13px] text-[13px] leading-relaxed syn-serif text-[#3e3347] dark:text-[#f1e9f4]">
                  {data.explanation}
                </div>
              )}

              {/* 4. Life Scenes (.life-scene) */}
              {data.scenes && data.scenes.length > 0 ? (
                <div className="space-y-2">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    КАК ЭТО ПРОЯВЛЯЕТСЯ В ЖИЗНИ
                  </h3>
                  <div className="space-y-2">
                    {data.scenes.map((scene, idx) => (
                      <div key={idx} className="rounded-[16px] bg-[#f8f5f8] dark:bg-[#251b2b] p-[12px] space-y-1">
                        <strong className="block text-[12px] font-bold text-[#3e3347] dark:text-[#f1e9f4]">
                          {scene.title}
                        </strong>
                        <span className="block text-[12px] leading-[1.45] text-[#65596a] dark:text-[#d4c8db]">
                          {scene.text}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              ) : data.scenario ? (
                <div className="space-y-2">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    КАК ЭТО ПРОЯВЛЯЕТСЯ В ЖИЗНИ
                  </h3>
                  <div className="rounded-[16px] bg-[#f8f5f8] dark:bg-[#251b2b] p-[12px] text-[12px] leading-[1.45] text-[#65596a] dark:text-[#d4c8db]">
                    {data.scenario}
                  </div>
                </div>
              ) : null}

              {/* 5. Repairs / What helps (.repair-item) */}
              {data.repairs && data.repairs.length > 0 ? (
                <div className="space-y-2">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    ЧТО ПОМОГАЕТ
                  </h3>
                  <div className="space-y-2">
                    {data.repairs.map((repair, idx) => (
                      <div
                        key={idx}
                        className="grid grid-cols-[25px_1fr] items-start gap-2.5 rounded-[15px] border border-[#dce9e3] bg-[#f4faf7] dark:bg-[#1a2822] p-[10px]"
                      >
                        <span className="flex h-[25px] w-[25px] items-center justify-center rounded-[9px] bg-[#eaf5f0] text-[#43806d] text-[11px] font-[850]">
                          {idx + 1}
                        </span>
                        <p className="text-[12px] leading-relaxed text-[#52645d] dark:text-[#9bc9b8] m-0">
                          {repair}
                        </p>
                      </div>
                    ))}
                  </div>
                </div>
              ) : data.advice ? (
                <div className="space-y-2">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    ЧТО ПОМОГАЕТ
                  </h3>
                  <div className="rounded-[15px] border border-[#dce9e3] bg-[#f4faf7] dark:bg-[#1a2822] p-[10px] text-[12px] leading-relaxed text-[#52645d] dark:text-[#9bc9b8]">
                    {data.advice}
                  </div>
                </div>
              ) : null}

              {/* 6. Not means / Protection from fatalism (.not-means) */}
              {data.notMeans && data.notMeans.length > 0 && (
                <div className="space-y-2 pt-2 border-t border-[#e8e0e8]">
                  <h3 className="font-sans text-[11px] font-[850] uppercase tracking-[0.09em] text-[#795a86]">
                    ВАЖНО: ЭТО НЕ ОЗНАЧАЕТ
                  </h3>
                  <div className="flex flex-wrap gap-1.5">
                    {data.notMeans.map((item, idx) => (
                      <span
                        key={idx}
                        className="rounded-full bg-[#f3eff4] dark:bg-[#2d2233] text-[#695d6d] dark:text-[#d4c8db] text-[10px] font-[760] px-[9px] py-[7px]"
                      >
                        {item}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          ) : null}
        </div>

        {/* Footer CTA: .primary.full plum button */}
        <button
          type="button"
          onClick={onClose}
          className="w-full h-[50px] rounded-[17px] bg-[#795a86] text-white text-[16px] font-[760] transition active:scale-[0.99] flex-none"
        >
          Понятно
        </button>
      </div>
    </div>
  )
}
// END_BLOCK: ASPECT_DRILLDOWN_SHEET
