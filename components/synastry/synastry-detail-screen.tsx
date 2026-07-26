// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_DETAIL_SCREEN
// ROLE: Detailed pair synastry report screen component
// DEPENDENCIES: react, lucide-react, lib/api/synastry, components/synastry/*
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-DETAIL-SCREEN
// purpose: Render full pair synastry report composed of pair-hero, score-panel, wheel/aspect-list, house-overlays, translations, spheres, and feedback.
// owns:
//   - components/synastry/synastry-detail-screen.tsx
// inputs: partnerId, onBack
// outputs: SynastryDetailScreen TSX render
// dependencies: lib/api/synastry, components/synastry/*
// side_effects: fetches report data, submits reality check feedback
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-DETAIL-SCREEN

// START_MODULE_MAP: M-SYNASTRY-DETAIL-SCREEN
// public_entrypoints:
//   - SynastryDetailScreen
// semantic_blocks:
//   - SYNASTRY_DETAIL_SCREEN: Pair synastry report screen component
// owned_tests:
//   - __tests__/synastry/synastry-detail-screen.test.tsx
// END_MODULE_MAP: M-SYNASTRY-DETAIL-SCREEN

"use client"

import { useEffect, useState } from "react"
import { ArrowLeft, ChevronDown, ChevronUp, AlertCircle, Sparkles } from "lucide-react"
import {
  getSynastryReport,
  getSynastryStatus,
  submitSynastryFeedback,
  type SynastryGenerationStatus,
  type SynastryReportData,
} from "@/lib/api/synastry"
import { SynastryPairHero } from "./synastry-pair-hero"
import { SynastryScorePanel } from "./synastry-score-panel"
import { SynastryAspectRow } from "./synastry-aspect-row"
import { SynastryHouseOverlays } from "./synastry-house-overlays"
import { SynastryTranslations } from "./synastry-translations"
import { SynastrySpheres } from "./synastry-spheres"
import { SynastryFeedbackBlock } from "./synastry-feedback"
import { AspectDrilldownSheet } from "./aspect-drilldown-sheet"
import { SynastryWheel, type SynastryWheelSelection } from "./synastry-wheel"

type Props = {
  partnerId: string
  onBack: () => void
}

// START_BLOCK: SYNASTRY_DETAIL_SCREEN
export function SynastryDetailScreen({ partnerId, onBack }: Props) {
  const [report, setReport] = useState<SynastryReportData | null>(null)
  const [genStatus, setGenStatus] = useState<SynastryGenerationStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [showAllAspects, setShowAllAspects] = useState(false)
  const [activeDrilldownAspect, setActiveDrilldownAspect] = useState<string | null>(null)
  const [drilldownOpen, setDrilldownOpen] = useState(false)

  const [selection, setSelection] = useState<SynastryWheelSelection>({
    selectedPlanetId: null,
    selectedAspectId: null,
  })

  const [feedbackValue, setFeedbackValue] = useState<string | null>(null)
  const [submittingFeedback, setSubmittingFeedback] = useState(false)

  useEffect(() => {
    let active = true
    let done = false
    let timer: ReturnType<typeof setInterval> | null = null

    const finish = () => {
      done = true
      if (timer) clearInterval(timer)
    }

    async function fetchReportOrStatus() {
      setError(null)
      try {
        const res = await getSynastryReport(partnerId)
        if (!active) return
        setReport(res)
        setFeedbackValue(res.userFeedback)
        setGenStatus(null)
        setLoading(false)
        finish()
      } catch {
        if (!active) return
        try {
          const st = await getSynastryStatus(partnerId)
          if (!active) return
          setGenStatus(st)

          if (st.state === "ready") {
            const res = await getSynastryReport(partnerId)
            if (!active) return
            setReport(res)
            setFeedbackValue(res.userFeedback)
            setLoading(false)
            finish()
          } else if (st.state === "failed") {
            setError("Не удалось выполнить расчёт. Попробуйте ещё раз.")
            setLoading(false)
            finish()
          } else {
            setLoading(true)
          }
        } catch {
          if (!active) return
          setError("Не удалось загрузить отчёт. Попробуйте ещё раз.")
          setLoading(false)
          finish()
        }
      }
    }

    void fetchReportOrStatus()

    timer = setInterval(async () => {
      if (!active || done) return
      try {
        const st = await getSynastryStatus(partnerId)
        if (!active) return
        setGenStatus(st)
        if (st.state === "ready") {
          const res = await getSynastryReport(partnerId)
          if (!active) return
          setReport(res)
          setFeedbackValue(res.userFeedback)
          setLoading(false)
          if (timer) clearInterval(timer)
        } else if (st.state === "failed") {
          setError("Не удалось выполнить расчёт. Попробуйте ещё раз.")
          setLoading(false)
          if (timer) clearInterval(timer)
        }
      } catch {
        /* ignore polling errors */
      }
    }, 2500)

    return () => {
      active = false
      if (timer) clearInterval(timer)
    }
  }, [partnerId])

  function handlePlanetSelect(planetId: string | null) {
    setSelection({
      selectedPlanetId: planetId,
      selectedAspectId: null,
    })
  }

  function handleAspectSelect(aspectId: string | null) {
    setSelection({
      selectedPlanetId: null,
      selectedAspectId: aspectId,
    })
  }

  function handleOpenAspectDrilldown(aspectId: string) {
    if (!aspectId) return
    setSelection({
      selectedPlanetId: null,
      selectedAspectId: aspectId,
    })
    setActiveDrilldownAspect(aspectId)
    setDrilldownOpen(true)
  }

  async function handleFeedbackSelect(val: string) {
    if (submittingFeedback || !report) return
    setSubmittingFeedback(true)
    setFeedbackValue(val)

    try {
      await submitSynastryFeedback(partnerId, val)
    } catch {
      // Retain optimistic UI state
    } finally {
      setSubmittingFeedback(false)
    }
  }

  if (loading) {
    const isCalculating = genStatus?.state === "calculating" || genStatus?.state === "pending" || !genStatus
    const isNarrating = genStatus?.state === "narrative_generating"

    return (
      <div
        className="flex min-h-[320px] flex-col items-center justify-center p-6 text-center space-y-6"
        data-testid="synastry-detail-screen"
        data-state="loading"
        role="status"
        aria-live="polite"
      >
        <div className="flex h-16 w-16 items-center justify-center rounded-full bg-[#795a86]/10 text-[#795a86] animate-pulse">
          <Sparkles className="h-8 w-8" />
        </div>

        <div className="space-y-1">
          <h2 className="syn-serif text-[22px] font-semibold text-[#3e3347] dark:text-[#f1e9f4]">
            Строим карту взаимодействия
          </h2>
          <p className="text-[13px] text-[#7d7284]">
            Рассчитываем планеты, аспекты и уникальную динамику пары
          </p>
        </div>

        {/* Staged progress items */}
        <div className="w-full max-w-xs space-y-2.5 text-left text-[13.5px] rounded-[20px] border border-[#e8e0e8] bg-white dark:bg-[#2d2233] p-4 shadow-sm">
          <div className="flex items-center gap-2.5 text-[#43806d] font-medium">
            <span>✓</span>
            <span>Сопоставили планеты</span>
          </div>
          <div className={`flex items-center gap-2.5 ${isCalculating ? "text-[#795a86] font-medium" : "text-[#43806d] font-medium"}`}>
            <span>{isNarrating ? "✓" : "•"}</span>
            <span>Рассчитываем аспекты</span>
          </div>
          <div className={`flex items-center gap-2.5 ${isNarrating ? "text-[#795a86] font-medium" : "text-[#7d7284]"}`}>
            <span>•</span>
            <span>Готовим человеческий перевод</span>
          </div>
        </div>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="p-5 space-y-4" data-testid="synastry-detail-screen" data-state="error">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-[13px] text-[#7d7284] hover:text-[#3e3347]"
        >
          <ArrowLeft className="h-4 w-4" /> Назад к списку
        </button>
        <div className="rounded-[18px] border border-destructive/20 bg-destructive/10 p-5 text-center space-y-3" role="alert">
          <AlertCircle className="mx-auto h-7 w-7 text-destructive" />
          <h2 className="syn-serif text-[18px] font-semibold text-foreground">Не удалось загрузить отчёт</h2>
          <p className="text-[13px] text-destructive">{error || "Не удалось загрузить отчёт."}</p>
        </div>
      </div>
    )
  }

  const isApproximate = report.precision === "approximate"
  const visibleAspects = showAllAspects ? report.aspects : report.aspects.slice(0, 3)

  return (
    <div className="space-y-5 pb-16" data-testid="synastry-detail-screen" data-state="ready">
      {/* 1. PAIR HERO */}
      <SynastryPairHero
        partnerName={report.partnerName}
        relationType={report.relationType}
        partnerBirthDate={report.partnerBirthDate || report.createdAt}
        partnerBirthTime={report.partnerBirthTime}
        partnerBirthCity={report.partnerBirthCity}
        precision={report.precision}
        onBack={onBack}
      />

      {/* 2. SCORE PANEL */}
      <SynastryScorePanel
        score={report.score}
        status={report.status}
        verdict={report.verdict}
        summary={report.summary}
        heroTitle={report.heroTitle}
        heroDescription={report.heroDescription}
        counters={report.counters}
      />

      {/* 3. INTERACTION MAP (WHEEL & ASPECT LIST) */}
      <section
        className="mx-4 rounded-[26px] border border-[#e8e0e8] bg-[#fffdf9]/94 dark:bg-[#2d2233]/94 p-[18px] shadow-[0_8px_26px_rgba(73,51,82,0.055)] space-y-4"
        data-testid="synastry-wheel"
      >
        <div className="space-y-0.5">
          <span className="text-[11px] font-bold uppercase tracking-[0.14em] text-[#795a86]">
            КАРТА ВЗАИМОДЕЙСТВИЯ
          </span>
          <h2 className="syn-serif text-[22px] font-semibold text-[#3e3347] dark:text-[#f1e9f4]">
            Где между вами ток
          </h2>
          <p className="text-[13px] text-[#7d7284] dark:text-muted-foreground leading-relaxed">
            Два кольца — ваши планеты. Зелёные линии поддерживают, жёлтые раскачивают, красные дают трение. Нажми на линию или контакт ниже.
          </p>
        </div>

        {/* SVG Synastry Wheel */}
        <SynastryWheel
          ownerPlanets={report.ownerPlanets}
          partnerPlanets={report.partnerPlanets}
          aspects={report.aspects}
          precision={report.precision}
          partnerName={report.partnerName}
          selection={selection}
          onPlanetSelect={handlePlanetSelect}
          onAspectSelect={handleAspectSelect}
          onAspectOpen={handleOpenAspectDrilldown}
        />

        {/* Key Aspects List */}
        <div className="space-y-2.5 pt-1" id="synastry-aspects-list">
          {visibleAspects.map((aspect) => (
            <SynastryAspectRow
              key={aspect.id}
              aspect={aspect}
              onClick={handleOpenAspectDrilldown}
            />
          ))}
        </div>

        {report.aspects.length > 3 && (
          <button
            type="button"
            aria-expanded={showAllAspects}
            aria-controls="synastry-aspects-list"
            onClick={() => setShowAllAspects(!showAllAspects)}
            className="flex items-center justify-center gap-1 text-[13px] font-[830] text-[#795a86] hover:underline bg-transparent py-2 w-auto mx-auto border-0 cursor-pointer"
          >
            {showAllAspects ? (
              <>Скрыть второстепенные аспекты ↑</>
            ) : (
              <>Показать все аспекты ({report.aspects.length}) ↓</>
            )}
          </button>
        )}
      </section>

      {/* 4. HOUSE OVERLAYS */}
      <SynastryHouseOverlays
        houseOverlays={report.houseOverlays}
        houseSystem={report.houseSystem}
        isApproximate={isApproximate}
      />

      {/* 5. HUMAN TRANSLATIONS */}
      <SynastryTranslations
        translations={report.translations}
        onOpenAspect={handleOpenAspectDrilldown}
      />

      {/* 6. SPHERES */}
      <SynastrySpheres spheres={report.spheres} />

      {/* 7. REALITY CHECK FEEDBACK */}
      <SynastryFeedbackBlock
        feedbackValue={feedbackValue}
        onSubmitFeedback={handleFeedbackSelect}
        submitting={submittingFeedback}
      />

      {/* DRILL-DOWN SHEET MODAL */}
      <AspectDrilldownSheet
        open={drilldownOpen}
        partnerId={partnerId}
        aspectId={activeDrilldownAspect}
        onClose={() => setDrilldownOpen(false)}
      />
    </div>
  )
}
// END_BLOCK: SYNASTRY_DETAIL_SCREEN
