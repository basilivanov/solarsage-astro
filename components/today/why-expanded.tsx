// ############################################################################
// AI_HEADER: MODULE_TODAY_WHY_EXPANDED — progressive human and technical V2 explanation.
// ROLE: Keeps life-situation explanation first and confines astrology terms to
//       an explicitly opened nested calculation disclosure.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-WHY-EXPANDED
// purpose: Render controlled/uncontrolled Why disclosure for V2 and legacy Today payloads.
// owns:
//   - components/today/why-expanded.tsx
// inputs: legacy sections, backend v2.horizons / v2.whyToday / legacy-v2 evidence, wire identity, controlled open state, deeplink search params.
// outputs: data-testid="why-expanded" section with backend-horizons, horizons-unavailable, legacy-v2, human-only, or legacy disclosure branches.
// dependencies: next/navigation, contracts, presentation helpers, lib/icons, why-time-horizon-card.
// side_effects: controlled state callbacks and local technical disclosure state.
// emitted_logs: none.
// invariants:
//   - human V2 content does not leak technical astrology vocabulary.
//   - technical terminology is confined to the clearly marked calculation disclosure control and its opened content, never the human narrative.
//   - ?why=1 and ?why=1&astro=1 remain supported.
//   - Legacy selector is resolved only for exact previous accepted pair.
//   - Current/missing/mismatched identity never infers horizons.
// failure_policy: fail-closed unavailable for incompatible or missing wire identity; never fabricates backend horizons.
// END_MODULE_CONTRACT: M-TODAY-WHY-EXPANDED

// START_MODULE_MAP: M-TODAY-WHY-EXPANDED
// public_entrypoints:
//   - WhyExpanded
//   - resolveWhyExpandedMode
// semantic_blocks:
//   - MODE_RESOLUTION: backend-horizons / horizons-unavailable / legacy-v2 / human-only / legacy / empty branch selection.
//   - WHY_DISCLOSURE: controlled/uncontrolled top-level disclosure.
//   - BACKEND_HORIZONS_CONTENT: backend-owned horizons intro and card list.
//   - UNAVAILABLE_CONTENT: honest backend horizons-unavailable state.
//   - V2_WHY_CONTENT: legacy selector-derived three human time horizons and nested calculation.
//   - TECHNICAL_CALCULATION: selected evidence grouped by horizon.
// owned_tests:
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
//   - e2e/mock-visual/day-v2.spec.ts
// END_MODULE_MAP: M-TODAY-WHY-EXPANDED

"use client"

import { useEffect, useId, useRef, useState } from "react"
import { ChevronDown, ChevronUp } from "lucide-react"
import { useSearchParams } from "next/navigation"
import type { ConcreteAdviceBlock, TodayV2Block, TodayV2WhyTodayItem, TodayWhySection, TodayWireIdentity } from "@/lib/contracts/today"
import { getIcon } from "@/lib/icons"
import {
  formatActivationEvidenceTitle,
  formatOrb,
  getEvidenceDurationLabel,
  getEvidenceStageLabel,
  getSafeWhyTodayItem,
  getTechnicalEvidenceExplanation,
  getTechniqueLabel,
  selectWhyTimeHorizons,
} from "@/lib/presentation/today-v2"
import { LegacyWhyTimeHorizonCard, WhyTimeHorizonCard } from "./why-time-horizon-card"

type Props = {
  sections: TodayWhySection[]
  keyInsight: string
  v2?: TodayV2Block | null
  wireIdentity?: TodayWireIdentity
  whyToday?: TodayV2WhyTodayItem[] | null
  concreteAdvice?: ConcreteAdviceBlock | null
  onSphereSelect?: (key: string) => void
  open?: boolean
  onOpenChange?: (open: boolean) => void
}

// Consumer routing constants — current and previous accepted wire pairs.
const CURRENT_PAYLOAD_VERSION = "today.v2.1" as const
const CURRENT_FRONTEND_VERSION = 3 as const
const PREVIOUS_PAYLOAD_VERSION = "today.v2" as const
const PREVIOUS_FRONTEND_VERSION = 2 as const

export function resolveWhyExpandedMode({
  v2,
  whyToday,
  sections,
  wireIdentity,
}: {
  v2?: TodayV2Block | null
  whyToday?: TodayV2WhyTodayItem[] | null
  sections: TodayWhySection[]
  wireIdentity?: TodayWireIdentity
}): "backend-horizons" | "horizons-unavailable" | "legacy-v2" | "human-only" | "legacy" | "empty" {
  // START_FUNCTION_CONTRACT: F-M-TODAY-WHY-EXPANDED.resolveWhyExpandedMode
  // purpose: Resolve Why rendering branch based on wire identity and V2 horizons.
  // inputs: v2, whyToday, sections, wireIdentity.
  // returns: rendering branch.
  // side_effects: none.
  // emitted_logs: none.
  // error_behavior: returns safest branch; never invokes legacy selector for current/mismatch.
  // END_FUNCTION_CONTRACT: F-M-TODAY-WHY-EXPANDED.resolveWhyExpandedMode
  if (!v2) {
    if ((whyToday ?? []).length > 0) return "human-only"
    if (sections.length > 0) return "legacy"
    return "empty"
  }

  // Determine wire identity pair
  const isCurrent = wireIdentity?.payloadVersion === CURRENT_PAYLOAD_VERSION
    && wireIdentity?.frontendPayloadVersion === CURRENT_FRONTEND_VERSION
  const isPrevious = wireIdentity?.payloadVersion === PREVIOUS_PAYLOAD_VERSION
    && wireIdentity?.frontendPayloadVersion === PREVIOUS_FRONTEND_VERSION
  const isKnownPair = isCurrent || isPrevious

  if (!isKnownPair) {
    // Mismatched or missing identity with V2 present → fail-closed unavailable
    return "horizons-unavailable"
  }

  if (v2.horizons) return "backend-horizons"

  // horizons is null
  if (isPrevious) return "legacy-v2"
  return "horizons-unavailable"
}

// START_BLOCK: WHY_DISCLOSURE
export function WhyExpanded({ sections, keyInsight, v2, wireIdentity, whyToday, concreteAdvice, onSphereSelect, open, onOpenChange }: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-WHY-EXPANDED.WhyExpanded
  // purpose: Render controlled human-first Why content and its optional technical subsection.
  // inputs: Props — backend-owned V2/legacy content, wireIdentity, optional parent state control.
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
  const effectiveWhyToday = v2?.whyToday.length ? v2.whyToday : whyToday ?? []
  const mode = resolveWhyExpandedMode({ v2, whyToday: effectiveWhyToday, sections, wireIdentity })
  const legacyHorizons = mode === "legacy-v2" && v2 ? selectWhyTimeHorizons(v2) : []
  const hasLegacyV2Horizons = legacyHorizons.length > 0
  const hasSafeWhyItems = effectiveWhyToday.length > 0
  const showWhyBlock = mode !== "empty" && (mode !== "legacy-v2" || hasLegacyV2Horizons || hasSafeWhyItems || sections.length > 0)

  useEffect(() => {
    if (isOpen && !wasOpen.current) setAstroOpen(defaultAstroOpen)
    wasOpen.current = isOpen
  }, [defaultAstroOpen, isOpen])

  if (!showWhyBlock) return null

  const setMainOpen = (next: boolean) => {
    if (open === undefined) setUncontrolledOpen(next)
    onOpenChange?.(next)
  }
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
                {mode === "legacy" ? "Почему так у меня" : "Почему именно у меня"}
              </span>
            </span>
          <span className="flex h-10 w-10 flex-none items-center justify-center rounded-full bg-violet-100 text-violet-700 dark:bg-violet-500/15 dark:text-violet-100">
            {isOpen ? <ChevronUp className="h-4 w-4" aria-hidden /> : <ChevronDown className="h-4 w-4" aria-hidden />}
          </span>
        </button>

        {isOpen ? (
          <div id={detailsId} className="border-t border-border/60 bg-gradient-to-br from-card to-violet-50/35 px-5 pb-6 pt-5 dark:to-violet-950/15">
            {mode === "backend-horizons" ? (
              <BackendHorizonsContent v2={v2} concreteAdvice={concreteAdvice} onSphereSelect={onSphereSelect} />
            ) : mode === "horizons-unavailable" ? (
              <HorizonsUnavailableContent />
            ) : mode === "legacy-v2" && hasLegacyV2Horizons ? (
              <V2WhyContent
                v2={v2}
                horizons={legacyHorizons}
                astroOpen={astroOpen}
                onAstroOpenChange={setAstroOpen}
                technicalId={technicalId}
              />
            ) : mode === "human-only" || (mode === "legacy-v2" && hasSafeWhyItems) ? (
              <HumanOnlyWhyContent items={effectiveWhyToday} />
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

function HorizonsUnavailableContent() {
  return (
    <section data-testid="why-horizons-unavailable" data-state="empty" data-source="backend-horizons" className="space-y-3">
      <h3 className="font-serif text-[20px] leading-snug text-foreground">Три временных горизонта пока недоступны</h3>
      <p className="text-[15px] leading-relaxed text-muted-foreground">
        Мы покажем их, когда получим подтверждённые сроки и персональные связи. Не будем заменять их приблизительной версией.
      </p>
    </section>
  )
}

function BackendHorizonsContent({
  v2,
  concreteAdvice,
  onSphereSelect,
}: {
  v2: TodayV2Block | null | undefined
  concreteAdvice?: ConcreteAdviceBlock | null
  onSphereSelect?: (key: string) => void
}) {
  if (!v2?.horizons) return null
  return (
    <section data-testid="why-horizons" data-state="ready" data-source="backend-horizons" className="space-y-4">
      <div>
        <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-200">{v2.horizons.intro.eyebrow}</p>
        <p className="mt-2 font-serif text-[23px] leading-[1.25] text-foreground">{v2.horizons.intro.headline}</p>
        <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">{v2.horizons.intro.body}</p>
      </div>
      <div className="space-y-3">
        {v2.horizons.items.map((horizon) => (
          <WhyTimeHorizonCard
            key={horizon.id}
            horizon={horizon}
            concreteAdvice={concreteAdvice}
            onSphereSelect={onSphereSelect}
          />
        ))}
      </div>
    </section>
  )
}

function V2WhyContent({
  v2,
  horizons,
  astroOpen,
  onAstroOpenChange,
  technicalId,
}: {
  v2: TodayV2Block | null | undefined
  horizons: ReturnType<typeof selectWhyTimeHorizons>
  astroOpen: boolean
  onAstroOpenChange: (open: boolean) => void
  technicalId: string
}) {
  if (!v2) return null
  return (
    <>
      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-200">Личная логика периода</p>
      <p className="mt-2 font-serif text-[23px] leading-[1.25] text-foreground">
        Это не три случайных факта. Один личный сюжет идёт в трёх скоростях.
      </p>
      <p className="mt-2 text-[15px] leading-relaxed text-muted-foreground">
        Он формируется в длинном цикле, усиливается в текущем периоде и получает короткий триггер сегодня.
      </p>
      <div data-testid="why-today" className="mt-5 space-y-3">
        {horizons.map((horizon) => <LegacyWhyTimeHorizonCard key={horizon.id} horizon={horizon} />)}
      </div>
      <TechnicalCalculation
        v2={v2}
        horizons={horizons}
        open={astroOpen}
        onOpenChange={onAstroOpenChange}
        technicalId={technicalId}
      />
    </>
  )
}

function HumanOnlyWhyContent({ items }: { items: TodayV2WhyTodayItem[] }) {
  return (
    <ol data-testid="why-today" className="space-y-5">
      {items.map((item, index) => {
        const safeItem = getSafeWhyTodayItem(item)
        return (
          <li key={item.id} data-testid="why-today-item" className="grid grid-cols-[auto_1fr] gap-3.5">
            <span className="flex h-8 w-8 items-center justify-center rounded-full border border-violet-200 bg-violet-50 text-[12px] font-semibold text-violet-700 dark:border-violet-400/30 dark:bg-violet-500/10 dark:text-violet-200">
              {String(index + 1).padStart(2, "0")}
            </span>
            <div>
              <h3 className="text-[16px] font-semibold leading-snug text-foreground">{safeItem.title}</h3>
              <p className="mt-1.5 font-serif text-[16px] leading-[1.55] text-foreground/85">{safeItem.body}</p>
            </div>
          </li>
        )
      })}
    </ol>
  )
}

function TechnicalCalculation({
  v2,
  horizons,
  open,
  onOpenChange,
  technicalId,
}: {
  v2: TodayV2Block
  horizons: ReturnType<typeof selectWhyTimeHorizons>
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
          <span className="block text-[17px] font-semibold text-foreground">Как мы это рассчитали</span>
          <span className="mt-0.5 block text-[13px] text-muted-foreground">Профекция, фирдар, транзиты и орбы — простыми словами</span>
        </span>
        {open ? <ChevronUp className="h-5 w-5 flex-none" aria-hidden /> : <ChevronDown className="h-5 w-5 flex-none" aria-hidden />}
      </button>
      {open ? (
        <div id={technicalId} className="border-t border-violet-200/70 px-4 pb-4 pt-3 dark:border-violet-400/20">
          <div className="space-y-4">
            {horizons.map((horizon) => (
              <section key={horizon.id} data-horizon={horizon.id} className="overflow-hidden rounded-xl border border-border/60 bg-card">
                <p className="border-b border-border/60 bg-violet-50/50 px-3.5 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-violet-700 dark:bg-violet-500/10 dark:text-violet-200">
                  {horizon.id === "long" ? "Большой сюжет" : horizon.id === "medium" ? "Активная волна" : "Триггер сегодня"}
                </p>
                {horizon.evidence.map((item) => {
                  const orb = formatOrb(item.orb)
                  const stage = getEvidenceStageLabel(item.phase)
                  const explanation = getTechnicalEvidenceExplanation(item)
                  return (
                    <article key={item.id} data-testid="astrology-calculation-item" data-horizon={horizon.id} data-polarity={item.polarity || "neutral"} className="border-b border-border/60 px-3.5 py-3 last:border-b-0">
                      <p className="text-[15px] font-semibold leading-snug text-foreground">{formatActivationEvidenceTitle(item)}</p>
                      <p className="mt-1 text-[13px] font-medium text-violet-700 dark:text-violet-200">{getTechniqueLabel(item.technique)}</p>
                      <p className="mt-1 text-[14px] text-muted-foreground">{getEvidenceDurationLabel(item)}</p>
                      <p className="mt-1 text-[14px] text-muted-foreground">{[stage, orb ? `орб ${orb}` : null].filter(Boolean).join(" · ")}</p>
                      <p className="mt-3 text-[13px] font-semibold text-foreground">Что это такое</p>
                      <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{explanation.definition}</p>
                      <p className="mt-3 text-[13px] font-semibold text-foreground">Что означает именно здесь</p>
                      <p className="mt-1 text-[13px] leading-relaxed text-muted-foreground">{explanation.meaning}</p>
                    </article>
                  )
                })}
              </section>
            ))}
          </div>
          <p className="mt-3 text-[13px] leading-relaxed text-muted-foreground">
            V2 передал {v2.activationEvidence.filter((item) => item.active !== false).length} активных подтверждений из {new Set(v2.activationEvidence.filter((item) => item.active !== false).map((item) => item.techniqueFamily)).size} независимых методов. Здесь показаны {horizons.reduce((sum, horizon) => sum + horizon.evidence.length, 0)} самых сильных сигналов, которые поддерживают главный личный сюжет.
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
