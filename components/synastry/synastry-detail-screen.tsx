// ############################################################################
// AI_HEADER: MODULE_SYNASTRY_DETAIL_SCREEN
// ROLE: Detailed pair synastry report screen component
// DEPENDENCIES: react, lucide-react, lib/api/synastry
// ############################################################################

// START_MODULE_CONTRACT: M-SYNASTRY-DETAIL-SCREEN
// purpose: Render full pair synastry report including hero, score, wheel/aspects, house overlays, translations, spheres, and reality check feedback.
// owns:
//   - components/synastry/synastry-detail-screen.tsx
// inputs: partnerId, onBack
// outputs: SynastryDetailScreen TSX render
// dependencies: lib/api/synastry, components/synastry/aspect-drilldown-sheet
// side_effects: fetches report data, submits reality check feedback
// emitted_logs: none
// failure_policy: inline error state
// END_MODULE_CONTRACT: M-SYNASTRY-DETAIL-SCREEN

// START_MODULE_MAP: M-SYNASTRY-DETAIL-SCREEN
// public_entrypoints:
//   - SynastryDetailScreen
// semantic_blocks:
//   - SYNASTRY_DETAIL_SCREEN: Pair synastry report screen component
// owned_tests: none
// END_MODULE_MAP: M-SYNASTRY-DETAIL-SCREEN

"use client"

import { useEffect, useState } from "react"
import { ArrowLeft, ChevronDown, ChevronUp, AlertCircle, Info } from "lucide-react"
import {
  getSynastryReport,
  submitSynastryFeedback,
  type SynastryReportData,
} from "@/lib/api/synastry"
import { AspectDrilldownSheet } from "./aspect-drilldown-sheet"

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
  const [openSpheres, setOpenSpheres] = useState<Record<string, boolean>>({})

  const [activeDrilldownAspect, setActiveDrilldownAspect] = useState<string | null>(null)
  const [drilldownOpen, setDrilldownOpen] = useState(false)

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

  function handleOpenAspectDrilldown(aspectId: string) {
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

  function toggleSphere(id: string) {
    setOpenSpheres((prev) => ({ ...prev, [id]: !prev[id] }))
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
        <div className="rounded-2xl border border-destructive/20 bg-destructive/10 p-5 text-center space-y-2">
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
    <div className="space-y-6 pb-12" data-testid="synastry-detail-screen" data-state="ready">
      {/* Top bar navigation */}
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={onBack}
          className="inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-card px-3.5 py-1.5 text-[13px] font-medium text-foreground transition active:scale-95"
        >
          <ArrowLeft className="h-4 w-4" /> Назад
        </button>
        <span className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Совместимость
        </span>
      </div>

      {/* 1. HERO */}
      <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-3" data-testid="synastry-hero">
        <div className="flex items-center gap-3">
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary font-serif font-bold text-[18px]">
            Ты
          </div>
          <span className="text-[18px] font-bold text-muted-foreground">+</span>
          <div className="flex h-12 w-12 items-center justify-center rounded-full bg-accent/20 text-accent-foreground font-serif font-bold text-[18px]">
            {report.partnerName.slice(0, 1)}
          </div>
          <div>
            <h1 className="font-serif text-[22px] font-semibold text-foreground leading-snug">
              Ты и {report.partnerName}
            </h1>
            <span className="text-[12px] text-muted-foreground capitalize">
              {report.relationType === "romantic" ? "Романтическая пара" : report.relationType}
            </span>
          </div>
        </div>

        {isApproximate && (
          <div className="inline-flex items-center gap-1.5 rounded-full border border-amber-500/30 bg-amber-500/10 px-3 py-1 text-[11.5px] font-medium text-amber-800 dark:text-amber-200">
            <Info className="h-3.5 w-3.5" />
            Примерный расчёт (без точного времени)
          </div>
        )}
      </section>

      {/* 2. SCORE & VERDICT */}
      <section
        className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-4"
        data-testid="synastry-score"
        data-status={report.status}
      >
        <div className="flex items-baseline justify-between">
          <div className="flex items-baseline gap-2">
            <span className="font-serif text-[42px] font-extrabold leading-none text-primary">
              {report.score}
            </span>
            <span className="text-[15px] font-medium text-muted-foreground">/ 100</span>
          </div>
          <span
            className={`rounded-full px-3 py-1 text-[11px] font-bold uppercase tracking-wider ${
              report.status === "good"
                ? "bg-emerald-500/15 text-emerald-600 dark:text-emerald-300"
                : report.status === "bad"
                ? "bg-destructive/15 text-destructive"
                : "bg-amber-500/15 text-amber-600 dark:text-amber-300"
            }`}
          >
            {report.status === "good" ? "Отличная связь" : report.status === "bad" ? "Высокое трение" : "Нормальный потенциал"}
          </span>
        </div>

        <div>
          <h2 className="font-serif text-[19px] font-semibold text-foreground">{report.verdict}</h2>
          <p className="mt-1.5 text-[14px] leading-relaxed text-muted-foreground">{report.summary}</p>
        </div>

        <div className="flex items-center gap-4 pt-2 border-t border-border/40 text-[12px] font-medium text-muted-foreground">
          <span className="text-emerald-600 dark:text-emerald-400">✦ {report.counters.good} поддерживают</span>
          <span className="text-amber-600 dark:text-amber-400">✦ {report.counters.mid} неоднозначны</span>
          <span className="text-destructive">✦ {report.counters.bad} напрягают</span>
        </div>
      </section>

      {/* 3. WHEEL & ASPECTS */}
      <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-wheel">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Карта взаимодействия (Аспекты)
        </h3>

        <div className="space-y-2.5" id="synastry-aspects-list">
          {visibleAspects.map((aspect) => (
            <button
              key={aspect.id}
              type="button"
              data-testid="synastry-aspect"
              data-tone={aspect.tone}
              onClick={() => handleOpenAspectDrilldown(aspect.id)}
              className="flex w-full items-center justify-between rounded-2xl border border-border/60 bg-background/60 p-4 text-left transition hover:border-primary/50 active:scale-[0.99]"
            >
              <div>
                <div className="text-[14.5px] font-semibold text-foreground">{aspect.title}</div>
                {aspect.description && (
                  <div className="mt-0.5 text-[12.5px] text-muted-foreground">{aspect.description}</div>
                )}
              </div>
              <span className="text-[12px] font-medium text-primary flex-none">Подробнее →</span>
            </button>
          ))}
        </div>

        {report.aspects.length > 3 && (
          <button
            type="button"
            aria-expanded={showAllAspects}
            aria-controls="synastry-aspects-list"
            onClick={() => setShowAllAspects(!showAllAspects)}
            className="w-full flex items-center justify-center gap-1.5 rounded-xl border border-border/70 bg-muted/40 py-2.5 text-[13px] font-medium text-foreground transition active:scale-[0.99]"
          >
            {showAllAspects ? (
              <>Скрыть аспекты <ChevronUp className="h-4 w-4" /></>
            ) : (
              <>Показать все аспекты ({report.aspects.length}) <ChevronDown className="h-4 w-4" /></>
            )}
          </button>
        )}
      </section>

      {/* 4. HOUSE OVERLAYS */}
      <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-3" data-testid="synastry-overlays">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Наложение домов
        </h3>

        {isApproximate ? (
          <div className="rounded-2xl border border-border/60 bg-muted/30 p-4 text-[13px] text-muted-foreground italic">
            Без точного времени рождения нельзя определить наложение домов партнёра.
          </div>
        ) : report.houseOverlays.length > 0 ? (
          <div className="space-y-2.5">
            {report.houseOverlays.map((item, i) => (
              <div key={i} className="rounded-2xl border border-border/60 bg-background/50 p-4 space-y-1">
                {item.tech && <div className="text-[11px] font-medium text-muted-foreground">{item.tech}</div>}
                <div className="text-[13.5px] text-foreground leading-relaxed">{item.text}</div>
              </div>
            ))}
          </div>
        ) : (
          <div className="text-[13px] text-muted-foreground">Наложения домов рассчитываются.</div>
        )}
      </section>

      {/* 5. HUMAN TRANSLATIONS */}
      {report.translations.length > 0 && (
        <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-translations">
          <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
            Человеческий перевод
          </h3>

          <div className="space-y-3">
            {report.translations.map((item, idx) => (
              <div key={idx} className="rounded-2xl border border-border/70 bg-background/60 p-4 space-y-2">
                <div className="flex items-center justify-between">
                  <h4 className="font-serif text-[16px] font-semibold text-foreground">{item.title}</h4>
                  {item.tech && (
                    <button
                      type="button"
                      onClick={() => handleOpenAspectDrilldown(item.tech || "")}
                      className="text-[11px] font-medium text-primary underline"
                    >
                      Что значит?
                    </button>
                  )}
                </div>
                {item.text && <p className="text-[13.5px] text-foreground/85 leading-relaxed">{item.text}</p>}
                {item.scene && (
                  <p className="text-[12.5px] text-muted-foreground italic border-t border-border/30 pt-2">
                    Сцена из жизни: «{item.scene}»
                  </p>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {/* 6. SPHERES */}
      <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-spheres">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Сферы отношений
        </h3>

        <div className="space-y-3">
          {report.spheres.map((sphere) => {
            const isOpen = !!openSpheres[sphere.id]
            return (
              <div key={sphere.id} className="rounded-2xl border border-border/70 bg-background/50 overflow-hidden">
                <button
                  type="button"
                  aria-expanded={isOpen}
                  onClick={() => toggleSphere(sphere.id)}
                  className="w-full flex items-center justify-between p-4 text-left font-medium"
                >
                  <div className="flex items-center gap-3">
                    <span className="font-serif text-[17px] font-semibold text-foreground">{sphere.title}</span>
                    <span className="rounded-full bg-primary/10 px-2.5 py-0.5 text-[12px] font-bold text-primary">
                      {sphere.score} / 100
                    </span>
                  </div>
                  {isOpen ? <ChevronUp className="h-4 w-4 text-muted-foreground" /> : <ChevronDown className="h-4 w-4 text-muted-foreground" />}
                </button>

                {isOpen && sphere.description && (
                  <div className="px-4 pb-4 text-[13.5px] text-muted-foreground border-t border-border/30 pt-3 leading-relaxed">
                    {sphere.description}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      </section>

      {/* 7. REALITY CHECK FEEDBACK */}
      <section className="rounded-3xl border border-border/70 bg-card p-6 shadow-sm space-y-4" data-testid="synastry-feedback">
        <h3 className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">
          Проверка реальностью
        </h3>
        <p className="text-[13.5px] text-foreground/85">Насколько разбор отозвался в вашем личном опыте?</p>

        <div className="grid grid-cols-3 gap-2">
          {[
            { id: "accurate", label: "Да, очень" },
            { id: "partial", label: "Частично" },
            { id: "inaccurate", label: "Не похоже" },
          ].map((option) => (
            <button
              key={option.id}
              type="button"
              aria-pressed={feedbackValue === option.id}
              onClick={() => handleFeedbackSelect(option.id)}
              className={`rounded-2xl border py-3 text-[13px] font-medium transition active:scale-95 ${
                feedbackValue === option.id
                  ? "border-primary bg-primary text-primary-foreground font-semibold"
                  : "border-border/70 bg-background text-foreground/80 hover:border-primary/50"
              }`}
            >
              {option.label}
            </button>
          ))}
        </div>

        <p className="text-[11.5px] text-muted-foreground text-center italic">
          Синастрия описывает астрологические паттерны, а не выносит приговор вашим отношениям.
        </p>
      </section>

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
