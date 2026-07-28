// ############################################################################
// AI_HEADER: MODULE_TODAY_TODAY_SCREEN
// ROLE: UI component — Reworked /day/[date] screen matching the mock-preview
//       visual oracle while keeping real SolarSage/API data.
// ############################################################################

// START_MODULE_CONTRACT: M-TODAY-TODAY-SCREEN
// purpose: Renders the minimal premium /day/[date] screen.
//          Accessible composition order: DateHeader → [TrialBanner/checkin] → DaySummaryCard →
//          ActivationEvidenceCard → ConcreteDayAdvice → WhyExpanded →
//          DayCollapsible (DayReading) → DayCollapsible (DayChart + DevAuditDrawer) → footer.
// owns:
//   - components/today/today-screen.tsx
// inputs:
//   - selectedDate, access, payload (AdaptedTodayPayload), calendarLunar,
//     onDateChange, importantToday
// outputs:
//   - TSX layout with data-testid="today-screen" and data-state="ready|locked"
// dependencies:
//   - today/* components
//   - next/navigation useSearchParams for Why deeplink defaults
//   - @/components/paywall, @/components/trial-banner
//   - @/lib/today, @/lib/access
// side_effects: Pointer/touch swipe handlers; controlled V2 selection/Why state;
//               post-commit smooth scroll and focus for hero navigation.
// invariants:
//   - data-state reflects the real access state (ready=accessible, locked=inaccessible)
//   - TrialBanner renders only for real trial access, never subscription/unmetered full access.
//   - data-testid attributes present on all major sections
//   - V2 sphere/Why state resets to the current deeplink default on date changes
//   - Loading/error states handled by the parent page
//   - payload.wireIdentity passed to WhyExpanded unchanged.
//   - selectPersonalStorySphere guards against non-existent row keys.
//   - scrollAndFocusSphere targets exact matching row (not container) with smooth/center + preventScroll.
//   - Same-key click repeats scroll/focus without deselection; missing target is no-op.
//   - DayReading and DayChart live inside collapsed DayCollapsible disclosures in accessible view
//   - WeekStrip and AstroHistoryWidget omitted from accessible stream (locked branch unchanged)
// failure_policy: renders gracefully; missing data hides sections silently
// END_MODULE_CONTRACT: M-TODAY-TODAY-SCREEN

// START_MODULE_MAP: M-TODAY-TODAY-SCREEN
// public_entrypoints:
//   - TodayScreen
// semantic_blocks:
//   - V2_NAVIGATION: useSearchParams deeplink defaults, controlled sphere/Why state, and post-commit scroll/focus.
//   - DAY_SWIPE: bounded pointer/touch date navigation.
//   - SCREEN_COMPOSITION: accessible and locked Today layouts with disclosure wrappers.
// owned_tests:
//   - __tests__/components/TodayScreen.test.tsx
//   - __tests__/components/TodayScreen.v2-downstream.test.tsx
// END_MODULE_MAP: M-TODAY-TODAY-SCREEN

"use client"

import { useEffect, useRef, useState } from "react"
import { useSearchParams } from "next/navigation"

import { DateHeader } from "./date-header"
import { TodayNotes } from "./today-notes"
import { DayReading } from "./day-reading"
import { WeekStrip } from "./week-strip"
import { DayChart } from "./day-chart"
import { DaySummaryCard } from "./day-summary-card"
import { ConcreteDayAdvice } from "./concrete-day-advice"
import { ActivationEvidenceCard } from "./activation-evidence-card"
import { TodayFocusCard } from "./today-focus"
import { DevAuditDrawer } from "./dev-audit-drawer"
import { AstroHistoryWidget } from "./astro-history-widget"
import { DayCollapsible } from "./day-collapsible"
import { SphereDetailsSheet } from "./sphere-details-sheet"
import { Paywall } from "@/components/paywall"
import { TrialBanner } from "@/components/trial-banner"
import { YesterdayEchoLoader } from "@/components/checkin/yesterday-echo"
import { addDays, sameDay, TODAY, type AdaptedTodayPayload } from "@/lib/today"
import { isDayAccessible, type AccessInfo } from "@/lib/access"
import type { CalendarLunarFields, TodayImportantEvent } from "@/packages/contracts"

type Props = {
  selectedDate: Date
  access: AccessInfo
  payload: AdaptedTodayPayload
  calendarLunar?: CalendarLunarFields | null
  onDateChange: (_d: Date) => void
  importantToday?: TodayImportantEvent[]
}

// Порог срабатывания свайпа — чтобы случайные жесты не перелистывали день
const SWIPE_THRESHOLD = 70
// Максимальное вертикальное смещение: если больше — это скролл, а не свайп
const SWIPE_MAX_VERTICAL = 50

// START_BLOCK: SCREEN_COMPOSITION
export function TodayScreen({
  selectedDate,
  access,
  payload,
  onDateChange,
}: Props) {
  // START_FUNCTION_CONTRACT: F-M-TODAY-TODAY-SCREEN.TodayScreen
  // purpose: Render the main screen for a specific day, handling access check, checkin, summary, advice, reading, why-expanded, and week strip sections.
  // inputs: Props containing selectedDate, access state, adapted payload, calendar fields, callbacks, and flags.
  // returns: Main Today layout JSX.
  // side_effects: coordinates sub-components, triggers scroll and focus transitions on sphere select or why expand, sets up swipe navigation handlers.
  // emitted_logs: none (delegates logs to child hooks/methods).
  // error_behavior: bubbles rendering exceptions to the parent boundary; missing optional data is hidden gracefully.
  // END_FUNCTION_CONTRACT: F-M-TODAY-TODAY-SCREEN.TodayScreen
  const searchParams = useSearchParams()
  const accessible = isDayAccessible(selectedDate, access)
  const isToday = sameDay(selectedDate, TODAY)
  const [selectedSphereKey, setSelectedSphereKey] = useState<string | null>(null)
  const whyDeeplinkDefault = searchParams?.get("why") === "1"

  // Навигация по дням: можно выходить только в пределах ±180 дней от сегодня
  const dayDiff = Math.round(
    (selectedDate.getTime() - TODAY.getTime()) / (1000 * 60 * 60 * 24),
  )
  const canPrev = dayDiff > -180
  const canNext = dayDiff < 180

  // Screen state for test contract
  const screenState = accessible ? "ready" : "locked"

  // --- Свайпы (pointer + touch fallback для iOS WKWebView) ---------------
  const start = useRef<{ x: number; y: number; id: number } | null>(null)

  useEffect(() => {
    setSelectedSphereKey(null)
  }, [selectedDate])

  function selectPersonalStorySphere(key: string) {
    // Guard: only open modal for existing rows
    if (!payload.concreteAdvice.rows.some((row) => row.key === key)) return
    setSelectedSphereKey(key)
  }

  useEffect(() => {
    if (!whyDeeplinkDefault) return
    const schedule = window.requestAnimationFrame ?? ((callback: FrameRequestCallback) => window.setTimeout(() => callback(Date.now()), 0))
    schedule(() => {
      document.querySelector('[data-testid="today-focus"]')?.scrollIntoView({ behavior: "smooth", block: "start" })
      const toggle = document.querySelector('[data-testid="today-focus-factor-toggle"]') as HTMLButtonElement | null
        ?? document.querySelector('[data-testid="today-focus-technical-toggle"]') as HTMLButtonElement | null
      if (toggle && toggle.getAttribute("aria-expanded") !== "true") {
        toggle.click()
      }
    })
  }, [whyDeeplinkDefault])

  function onPointerDown(e: React.PointerEvent<HTMLDivElement>) {
    start.current = { x: e.clientX, y: e.clientY, id: e.pointerId }
  }
  function onTouchStart(e: React.TouchEvent<HTMLDivElement>) {
    const t = e.touches[0]
    if (!t) return
    start.current = { x: t.clientX, y: t.clientY, id: t.identifier }
  }

  function onPointerUp(e: React.PointerEvent<HTMLDivElement>) {
    const s = start.current
    start.current = null
    if (!s || s.id !== e.pointerId) return

    const dx = e.clientX - s.x
    const dy = e.clientY - s.y

    if (Math.abs(dy) > SWIPE_MAX_VERTICAL) return
    if (Math.abs(dx) < Math.abs(dy)) return
    if (Math.abs(dx) < SWIPE_THRESHOLD) return

    if (dx < 0 && canNext) {
      onDateChange(addDays(selectedDate, 1))
    } else if (dx > 0 && canPrev) {
      onDateChange(addDays(selectedDate, -1))
    }
  }

  function onPointerCancel() {
    start.current = null
  }

  return (
    <div
      onPointerDown={onPointerDown}
      onPointerUp={onPointerUp}
      onPointerCancel={onPointerCancel}
      onTouchStart={onTouchStart}
      onTouchEnd={(e) => {
        const s = start.current
        start.current = null
        if (!s) return
        const t = e.changedTouches[0]
        if (!t) return
        const dx = t.clientX - s.x
        const dy = t.clientY - s.y
        if (Math.abs(dy) > SWIPE_MAX_VERTICAL) return
        if (Math.abs(dx) < Math.abs(dy)) return
        if (Math.abs(dx) < SWIPE_THRESHOLD) return
        if (dx < 0 && canNext) onDateChange(addDays(selectedDate, 1))
        else if (dx > 0 && canPrev) onDateChange(addDays(selectedDate, -1))
      }}
      className="touch-pan-y"
      data-testid="today-screen"
      data-state={screenState}
    >
      {/* Date Header with prev/next controls */}
      <div
        className="flex-none"
        style={{ paddingTop: "max(env(safe-area-inset-top), 0.5rem)" }}
        data-testid="day-header"
      >
        <DateHeader
          date={selectedDate}
          onPrev={() => onDateChange(addDays(selectedDate, -1))}
          onNext={() => onDateChange(addDays(selectedDate, 1))}
          canPrev={canPrev}
          canNext={canNext}
          locked={!accessible}
        />
      </div>

      {accessible ? (
        <div className="space-y-5 pb-8">
          {/* Trial-only access card */}
          {access.state === "trial" ? (
            <div data-testid="access-card">
              <TrialBanner daysLeft={access.daysLeft} />
            </div>
          ) : null}

          {isToday ? (
            <div className="px-5" data-testid="evening-checkin-reminder">
              <YesterdayEchoLoader />
            </div>
          ) : null}

          {/* Compact day summary card */}
          <DaySummaryCard
            date={selectedDate}
            dayStatus={payload.dayStatus}
            daySummary={payload.daySummary}
            humanFirst={Boolean(payload.v2)}
            relativeStatus={(payload as any).relativeStatus}
          />

          {/* Today Focus Block ("Что сошлось именно сегодня" / "События дня") */}
          <TodayFocusCard
            focus={payload.focus}
            onSphereSelect={selectPersonalStorySphere}
          />

          {/* Personal V2 story immediately below summary; null when V2 is absent. */}
          <ActivationEvidenceCard
            v2={payload.v2}
            concreteAdvice={payload.concreteAdvice}
            daySummary={payload.daySummary}
            onSphereSelect={selectPersonalStorySphere}
            headlineFallback={payload.headline}
          />

          <ConcreteDayAdvice
            concreteAdvice={payload.concreteAdvice}
            selectedKey={selectedSphereKey}
            onSelectedKeyChange={setSelectedSphereKey}
          />

          {/* Period Context Disclosure (Long-term horizon background) */}
          {payload.v2?.horizons?.items?.find((h) => h.horizon === "long") ? (
            <DayCollapsible title="Контекст периода" dataTestId="day-context-disclosure">
              {(() => {
                const longHorizon = payload.v2.horizons.items.find((h) => h.horizon === "long")!
                const title = longHorizon.title || "Долгий контекст периода"
                const eyebrow = longHorizon.eyebrow || "Долгий цикл"
                const summary = longHorizon.summary || null
                const plainExplanation = longHorizon.plainExplanation || null
                const rangeLabel = longHorizon.timing?.rangeLabel || null
                const stateLabel = longHorizon.timing?.stateLabel || null
                const manifestations = longHorizon.manifestations || []

                return (
                  <div className="space-y-4 text-foreground">
                    <div className="space-y-1">
                      <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-violet-700 dark:text-violet-300">
                        {eyebrow}
                      </p>
                      <h4 className="font-serif text-[20px] font-semibold leading-snug">
                        {title}
                      </h4>
                      {rangeLabel && (
                        <p className="text-[13px] font-medium text-muted-foreground">
                          {rangeLabel}{stateLabel ? ` · ${stateLabel}` : ""}
                        </p>
                      )}
                    </div>
                    {summary && (
                      <p className="text-[14.5px] leading-relaxed text-foreground/90 font-medium">
                        {summary}
                      </p>
                    )}
                    {plainExplanation && (
                      <p className="text-[14px] leading-relaxed text-muted-foreground">
                        {plainExplanation}
                      </p>
                    )}
                    {manifestations.length > 0 && (
                      <div className="space-y-1.5 pt-2 border-t border-border/40">
                        <p className="text-[12.5px] font-semibold uppercase tracking-[0.12em] text-violet-700 dark:text-violet-300">
                          Как проявляется
                        </p>
                        <ul className="space-y-1.5 pl-0 list-none text-[14px] leading-relaxed text-muted-foreground">
                          {manifestations.map((m: any, idx: number) => {
                            const text = typeof m === "string" ? m : m.body || m.title || ""
                            return (
                              <li key={idx} className="flex items-start gap-2">
                                <span className="h-1.5 w-1.5 rounded-full bg-violet-400 flex-none mt-2" aria-hidden="true" />
                                <span>{text}</span>
                              </li>
                            )
                          })}
                        </ul>
                      </div>
                    )}
                  </div>
                )
              })()}
            </DayCollapsible>
          ) : null}

          {/* Day reading disclosure */}
          <DayCollapsible title="Полный разбор дня" dataTestId="day-reading-disclosure">
            <DayReading paragraphs={payload.reading.paragraphs} />
          </DayCollapsible>

          {/* Technical calculation disclosure */}
          <DayCollapsible title="Как это рассчитано" dataTestId="day-tech-disclosure">
            <DayChart
              chart={payload.dayChart}
              dateLabel={formatDateLabel(selectedDate)}
              dayStatus={payload.dayStatus}
            />
            <DevAuditDrawer audit={payload.v2?.audit} />
          </DayCollapsible>
        </div>
      ) : (
        <div className="space-y-6 pb-8">
          {/* Access / paywall card */}
          <div data-testid="access-card">
            <Paywall
              title={
                isToday
                  ? "Твой персональный разбор на сегодня уже готов"
                  : "Этот день уже рассчитан для тебя"
              }
            />
          </div>

          {/* Preview notes */}
          <TodayNotes
            notes={payload.notes}
            limit={2}
            heading="Главное на этот день"
          />

          {/* Preview reading */}
          <DayReading paragraphs={payload.reading.paragraphs} preview />

          {/* Week strip */}
          <WeekStrip
            selectedDate={selectedDate}
            access={access}
            onSelect={onDateChange}
          />

          <AstroHistoryWidget date={selectedDate} />
        </div>
      )}

      {/* Footer disclaimer — stable across all states */}
      <footer className="px-5 pb-4 pt-2" data-testid="today-bottom-disclaimer">
        <p className="text-center font-sans text-[11px] leading-relaxed text-foreground/40">
          Данные показаны для ознакомления. Перед принятием важных решений проверяйте информацию.
        </p>
      </footer>

      {/* Sphere Details BottomSheet modal */}
      <SphereDetailsSheet
        row={
          selectedSphereKey
            ? payload.concreteAdvice.rows.find((r) => r.key === selectedSphereKey) || null
            : null
        }
        onClose={() => setSelectedSphereKey(null)}
      />
    </div>
  )
}
// END_BLOCK: SCREEN_COMPOSITION

function formatDateLabel(d: Date): string {
  const months = ["янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек"]
  return `${d.getDate()} ${months[d.getMonth()]}`
}
