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
import { ArrowLeft, ChevronDown, ChevronUp, AlertCircle } from "lucide-react"
import {
  getSynastryReport,
  submitSynastryFeedback,
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
    setLoading(true)
    setError(null)

    getSynastryReport(partnerId)
      .then((res) => {
        if (!active) return
        setReport(res)
        setFeedbackValue(res.userFeedback)
      })
      .catch((err) => {
        if (!active) return
        setError(err instanceof Error ? err.message : "Не удалось загрузить отчёт.")
      })
      .finally(() => {
        if (active) setLoading(false)
      })

    return () => {
      active = false
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
    return (
      <div className="flex h-64 flex-col items-center justify-center gap-3" data-testid="synastry-detail-screen" data-state="loading">
        <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        <span className="text-[13.5px] text-muted-foreground">Загружаем разбор совместимости…</span>
      </div>
    )
  }

  if (error || !report) {
    return (
      <div className="p-5 space-y-4" data-testid="synastry-detail-screen" data-state="error">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 text-[13px] text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" /> Назад к списку
        </button>
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-5 text-center space-y-2" role="alert">
          <AlertCircle className="mx-auto h-7 w-7 text-destructive" />
          <h2 className="font-serif text-[18px] font-semibold text-foreground">Не удалось загрузить отчёт</h2>
          <p className="text-[13px] text-muted-foreground">{error || "Ошибка загрузки данных"}</p>
        </div>
      </div>
    )
  }

  const isApproximate = report.precision === "approximate"
  const visibleAspects = showAllAspects ? report.aspects : report.aspects.slice(0, 3)

  return (
    <div className="space-y-6 pb-16" data-testid="synastry-detail-screen" data-state="ready">
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
      <section className="rounded-[24px] border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-wheel">
        <div className="space-y-1">
          <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            КАРТА ВЗАИМОДЕЙСТВИЯ
          </span>
          <h2 className="font-serif text-[22px] font-semibold text-foreground">
            Где между вами ток
          </h2>
          <p className="text-[13px] text-muted-foreground leading-relaxed">
            Взаимное расположение планет в двух натальных картах и линии связей.
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
        <div className="space-y-2.5 pt-2" id="synastry-aspects-list">
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
            className="w-full flex items-center justify-center gap-1.5 rounded-[16px] border border-border/70 bg-muted/40 py-3 text-[13px] font-medium text-foreground transition active:scale-[0.99]"
          >
            {showAllAspects ? (
              <>Скрыть второстепенные аспекты <ChevronUp className="h-4 w-4" /></>
            ) : (
              <>Показать все аспекты ({report.aspects.length}) <ChevronDown className="h-4 w-4" /></>
            )}
          </button>
        )}
      </section>

      {/* 4. HOUSE OVERLAYS */}
      <SynastryHouseOverlays
        houseOverlays={report.houseOverlays}
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
