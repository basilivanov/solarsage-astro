// ############################################################################
// AI_HEADER: MODULE_TODAY_WHY_EXPANDED — progressive human and technical V2 explanation.
// ROLE: Keeps life-situation explanation first and confines astrology terms to
//       an explicitly opened nested calculation disclosure.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-WHY-EXPANDED
// purpose: Render controlled/uncontrolled Why disclosure for V2 and legacy Today payloads.
// owns:
//   - components/today/why-expanded.tsx
// inputs: legacy sections, V2 data, controlled open state, deeplink search params.
// outputs: data-testid="why-expanded" section with optional technical disclosure.
// dependencies: next/navigation, contracts, presentation helpers, lib/icons.
// side_effects: controlled state callbacks and local technical disclosure state.
// emitted_logs: none.
// invariants:
//   - human V2 content does not leak technical astrology vocabulary.
//   - technical terminology exists only in opened astrology-calculation content.
//   - ?why=1 and ?why=1&astro=1 remain supported.
// failure_policy: legacy content remains readable without fabricated V2 evidence.
// END_MODULE_CONTRACT: M-TODAY-WHY-EXPANDED

"use client"

import { useEffect, useId, useRef, useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useSearchParams } from "next/navigation"
import type { TodayV2Block, TodayV2WhyTodayItem, TodayWhySection } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"
import {
  formatActivationEvidenceTitle,
  formatOrb,
  getPhaseLabelRu,
  getSafeWhyTodayItem,
  getTechniqueLabel,
  selectTechnicalCalculationEvidence,
} from "@/lib/presentation/today-v2"

type Props = {
  sections: TodayWhySection[]
  keyInsight: string
  v2?: TodayV2Block | null
  whyToday?: TodayV2WhyTodayItem[] | null
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// START_BLOCK: WHY_DISCLOSURE
export function WhyExpanded({ sections, keyInsight, v2, whyToday, open, onOpenChange }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-WHY-EXPANDED.WhyExpanded
  // purpose: Render controlled human-first Why content and its optional technical subsection.
  // inputs: Props — backend-owned V2/legacy content and optional parent state control.
  // returns: Why disclosure JSX or null.
  // side_effects: invokes onOpenChange and stores technical disclosure state.
  // emitted_logs: none.
  // error_behavior: returns null if neither legacy nor V2 content is available.
  // END_FUNCTION_CONTRACT: F-M-TODAY-WHY-EXPANDED.WhyExpanded
  const searchParams = useSearchParams()
  const defaultOpen = searchParams?.get("why") === "1"
  const defaultAstroOpen = defaultOpen && searchParams?.get("astro") === "1"
  const [uncontrolledOpen, setUncontrolledOpen] = useState(defaultOpen)
  const [astroOpen, setAstroOpen] = useState(defaultAstroOpen)
  const detailsId = useId()
  const technicalId = useId()
  const wasOpen = useRef(open ?? uncontrolledOpen)
  const isOpen = open ?? uncontrolledOpen
  const effectiveWhyToday = v2?.whyToday ?? whyToday ?? []
  const hasV2 = Boolean(v2 || effectiveWhyToday.length > 0)
  const showWhyBlock = hasV2 || sections.length > 0

  useEffect(() => {
    if (isOpen && !wasOpen.current) setAstroOpen(defaultAstroOpen)
    wasOpen.current = isOpen
  }, [defaultAstroOpen, isOpen])

  if (!showWhyBlock) return null

  const setMainOpen = (next: boolean) => {
    if (open === undefined) setUncontrolledOpen(next)
    onOpenChange?.(next)
  }
  const primary = v2?.activationSummary.topActivatedTargets[0]
  const technical = v2 ? selectTechnicalCalculationEvidence(v2.activationEvidence, primary) : null

  return (
    <section id="why-expanded" className="px-5" aria-label="Почему именно у меня" data-testid="why-expanded">
      <div className="overflow-hidden rounded-[24px] border border-violet-200/70 bg-card shadow-[0_16px_42px_-32px_rgba(109,40,217,0.45)] dark:border-violet-400/25">
        <button
          id="why-expanded-toggle"
          type="button"
          onClick={() => setMainOpen(!isOpen)}
          aria-expanded={isOpen}
          aria-controls={detailsId}
          className="flex min-h-16 w-full items-center justify-between gap-4 px-5 py-4 text-left transition hover:bg-violet-50/35 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-inset dark:hover:bg-violet-500/10"
        >
          <span className="min-w-0">
            <span className="block text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Глубже</span>
            <span className="mt-0.5 block font-serif text-[23px] leading-tight text-foreground">
              {hasV2 ? "Почему именно у меня" : "Почему так у меня"}
            </span>
          </span>
          <span className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-100">
            {isOpen ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
          </span>
        </button>

        {isOpen ? (
          <div id={detailsId} className="border-t border-border/60 bg-gradient-to-br from-card to-violet-50/35 px-5 pb-6 pt-5 dark:to-violet-950/15">
            {hasV2 ? (
              <V2WhyContent
                items={effectiveWhyToday}
                technical={technical}
                astroOpen={astroOpen}
                onAstroOpenChange={setAstroOpen}
                technicalId={technicalId}
              />
            ) : (
              <LegacyWhyContent sections={sections} keyInsight={keyInsight} />
            )}
          </div>
        ) : null}
      </div>
    </section>
  )
}
// END_BLOCK: WHY_DISCLOSURE

function V2WhyContent({
  items,
  technical,
  astroOpen,
  onAstroOpenChange,
  technicalId,
}: {
  items: TodayV2WhyTodayItem[]
  technical: ReturnType<typeof selectTechnicalCalculationEvidence> | null
  astroOpen: boolean
  onAstroOpenChange: (open: boolean) => void
  technicalId: string
}) {
  const safeItems = items.slice(0, 3).map(getSafeWhyTodayItem)
  return (
    <>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-200">Личная логика дня</p>
      <p className="mt-2 font-serif text-[23px] leading-[1.25] text-foreground">
        Сегодня одна и та же тема проявляется сразу на нескольких уровнях.
      </p>
      <div data-testid="why-today" className="mt-5 space-y-3">
        {safeItems.map((item, index) => (
          <article key={`${item.title}-${index}`} className="rounded-2xl border border-border/60 bg-card/85 p-4">
            <div className="flex items-start gap-3">
              <span className="flex h-9 w-9 flex-none items-center justify-center rounded-full bg-violet-100 text-[16px] font-semibold text-violet-800 dark:bg-violet-500/15 dark:text-violet-100">
                {index + 1}
              </span>
              <div className="min-w-0">
                <h3 className="text-[16px] font-semibold leading-snug text-foreground">{item.title}</h3>
                <p className="mt-1.5 text-[15px] leading-relaxed text-muted-foreground">{item.body}</p>
              </div>
            </div>
          </article>
        ))}
      </div>
      <TechnicalCalculation
        technical={technical}
        open={astroOpen}
        onOpenChange={onAstroOpenChange}
        technicalId={technicalId}
      />
    </>
  )
}

function TechnicalCalculation({
  technical,
  open,
  onOpenChange,
  technicalId,
}: {
  technical: ReturnType<typeof selectTechnicalCalculationEvidence> | null
  open: boolean
  onOpenChange: (open: boolean) => void
  technicalId: string
}) {
  return (
    <section data-testid="astrology-calculation" className="mt-5 overflow-hidden rounded-2xl border border-violet-200/70 bg-violet-50/35 dark:border-violet-400/25 dark:bg-violet-500/10">
      <button
        type="button"
        data-testid="astrology-calculation-toggle"
        aria-expanded={open}
        aria-controls={technicalId}
        onClick={() => onOpenChange(!open)}
        className="flex min-h-16 w-full items-center justify-between gap-4 px-4 py-3 text-left transition hover:bg-violet-100/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-violet-500 focus-visible:ring-inset dark:hover:bg-violet-500/10"
      >
        <span>
          <span className="block text-[17px] font-semibold text-foreground">Астрологический расчёт</span>
          <span className="mt-0.5 block text-[13px] text-muted-foreground">Для тех, кто хочет увидеть техническую основу</span>
        </span>
        {open ? <ChevronUp className="h-5 w-5 flex-none" aria-hidden /> : <ChevronDown className="h-5 w-5 flex-none" aria-hidden />}
      </button>
      {open ? (
        <div id={technicalId} className="border-t border-violet-200/70 px-4 pb-4 pt-3 dark:border-violet-400/20">
          <div className="overflow-hidden rounded-xl border border-border/60 bg-card">
            {technical?.aspects.map((item) => {
              const orb = formatOrb(item.orb)
              const phase = getPhaseLabelRu(item.phase)
              return (
                <article
                  key={item.id}
                  data-testid="astrology-calculation-item"
                  data-polarity={item.polarity || "neutral"}
                  className="border-b border-border/60 px-3.5 py-3 last:border-b-0"
                >
                  <p className="text-[15px] font-semibold leading-snug text-foreground">{formatActivationEvidenceTitle(item)}</p>
                  <p className="mt-1 text-[14px] text-muted-foreground">
                    {[orb ? `орб ${orb}` : null, phase].filter(Boolean).join(" · ")}
                  </p>
                </article>
              )
            })}
            {technical && technical.periodTechniques.length > 0 ? (
              <article data-testid="astrology-calculation-item" data-polarity="neutral" className="px-3.5 py-3">
                <p className="text-[15px] font-semibold text-foreground">Долгий личный фон</p>
                <p className="mt-1 text-[14px] text-muted-foreground">
                  {technical.periodTechniques.map(getTechniqueLabel).join(" · ")}
                </p>
              </article>
            ) : null}
          </div>
          <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
            Это расчёт, а не отдельный прогноз. Основные выводы уже переведены на язык жизненных ситуаций выше.
          </p>
        </div>
      ) : null}
    </section>
  )
}

function LegacyWhyContent({ sections, keyInsight }: { sections: TodayWhySection[]; keyInsight: string }) {
  return (
    <>
      <ol className="space-y-5">
        {sections.map((section, index) => {
          const Icon = getIcon(section.iconName)
          return (
            <li key={section.id} className="grid grid-cols-[auto_1fr] gap-3.5">
              <span className="flex h-8 w-8 items-center justify-center rounded-full border border-border/70 bg-card text-primary">
                <Icon className="h-4 w-4" strokeWidth={1.6} aria-hidden />
              </span>
              <div>
                <h3 className="text-[15px] font-semibold leading-snug text-foreground">{section.title}</h3>
                {section.paragraphs.map((paragraph, paragraphIndex) => (
                  <p key={paragraphIndex} className="mt-1.5 font-serif text-[16px] leading-[1.55] text-foreground/85">
                    {paragraph}
                  </p>
                ))}
              </div>
            </li>
          )
        })}
      </ol>
      <div className="mt-6 rounded-xl border border-border/70 bg-card px-4 py-3.5">
        <div className="text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">Ключ дня</div>
        <div className="mt-1 font-serif text-[17px] leading-snug text-foreground">{keyInsight}</div>
      </div>
    </>
  )
}
